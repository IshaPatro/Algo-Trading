import time
import datetime
import pandas as pd
import plotly.graph_objs as go
from dash import dcc, html
from dash.dependencies import Input, Output
import config
from threading import Thread, Event
from colors import *

data = []
stop_event = Event()

def stream_data(stop_event):
    retry_count = 0
    max_retries = 5
    retry_delay = 2
    
    while not stop_event.is_set():
        try:
            # Set a longer timeout for production environments
            config.client.request_timeout = 60
            response = config.client.request(config.r)
            prices = response["prices"]
            for price in prices:
                timestamp = datetime.datetime.now().isoformat()
                bid = float(price["bids"][0]["price"])
                ask = float(price["asks"][0]["price"])
                spread = (ask - bid)*10000
                new_data = {"Timestamp": timestamp, "Bid": bid, "Ask": ask, "Spread": spread}
                data.append(new_data)
            # Reset retry count on successful request
            retry_count = 0
            print(f"Successfully fetched price data at {timestamp}")
        except Exception as e:
            retry_count += 1
            print(f"Error fetching price data: {e} (Attempt {retry_count} of {max_retries})")
            if retry_count >= max_retries:
                print("Maximum retry attempts reached, waiting longer before next attempt")
                time.sleep(retry_delay * 5)
                retry_count = 0
            else:
                time.sleep(retry_delay)
            continue
        time.sleep(1)

def initialize_data_thread():
    thread = Thread(target=stream_data, args=(stop_event,))
    thread.daemon = True
    thread.start()
    return thread

def create_price_charts_layout():
    return html.Div([
        html.Div([
            html.Div([
                dcc.Graph(id="live-graph"),
            ], style={"width": "50%", "display": "inline-block"}),
            
            html.Div([
                dcc.Graph(id="spread-graph"),
            ], style={"width": "50%", "display": "inline-block"}),
        ]),
        
        html.Div([
            html.Div([
                dcc.Graph(id="sma-graph"),
            ], style={"width": "100%", "display": "block"}),
        ]),
        
        html.Div(id="charts-stats-container"),
    ], style={
        "backgroundColor": plot_bg_color,
        "padding": "15px",
        "borderRadius": "8px",
        "marginBottom": "20px"
    })

def register_callbacks(app):
    @app.callback(
        [Output("live-graph", "figure"), 
         Output("spread-graph", "figure"),
         Output("sma-graph", "figure"),
         Output("charts-stats-container", "children")],
        Input("interval-component", "n_intervals")
    )
    def update_graphs(n):
        df = pd.DataFrame(data)
        if df.empty:
            empty_figure = {
                "data": [],
                "layout": go.Layout(
                    title={"text": "Waiting for data...", "font": {"color": text_color}},
                    plot_bgcolor=plot_bg_color,
                    paper_bgcolor=dark_bg_color,
                    font={"color": text_color},
                )
            }
            empty_stats = html.Div("Waiting for price data...", 
                                 style={"color": text_color, "textAlign": "center", "padding": "20px"})
            return empty_figure, empty_figure, empty_figure, empty_stats
        
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        
        ten_minutes_ago = datetime.datetime.now() - datetime.timedelta(minutes=10)
        df = df[df["Timestamp"] >= ten_minutes_ago]
        
        if len(df) > 1:
            df["Price_Change"] = df["Bid"].diff().fillna(0)
            df["Volatility"] = df["Price_Change"].rolling(window=10).std().fillna(0) * 10000
            df["SMA_50"] = df["Bid"].rolling(window=config.SMA_50_WINDOW, min_periods=1).mean()
            df["SMA_200"] = df["Bid"].rolling(window=config.SMA_200_WINDOW, min_periods=50).mean()
           
            df["SMA_50_prev"] = df["SMA_50"].shift(1)
            df["SMA_200_prev"] = df["SMA_200"].shift(1)
            df["buy_signal"] = ((df["SMA_50"] > df["SMA_200"]) & (df["SMA_50_prev"] <= df["SMA_200_prev"]))
            
            df["sell_signal"] = ((df["SMA_50"] < df["SMA_200"]) & (df["SMA_50_prev"] >= df["SMA_200_prev"]))
            
            # Add profit booking and stop loss signals
            if config.trading_metrics["buy_avg_price"] > 0 and config.trading_metrics["total_buy_quantity"] > config.trading_metrics["total_sell_quantity"]:
                profit_threshold = config.trading_metrics["buy_avg_price"] + config.PROFIT_THRESHOLD_PIPS
                loss_threshold = config.trading_metrics["buy_avg_price"] - config.LOSS_THRESHOLD_PIPS
                
                df["profit_booking_signal"] = df["Bid"] >= profit_threshold
                df["stop_loss_signal"] = df["Bid"] <= loss_threshold
            else:
                df["profit_booking_signal"] = False
                df["stop_loss_signal"] = False
        else:
            df["Price_Change"] = 0
            df["Volatility"] = 0
            df["SMA_50"] = df["Bid"]
            df["SMA_200"] = df["Bid"]
            df["buy_signal"] = False
            df["sell_signal"] = False
            df["profit_booking_signal"] = False
            df["stop_loss_signal"] = False

        bid_ask_figure = {
            "data": [
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["Bid"],
                    mode="lines",
                    name="Bid Price",
                    line={"color": bid_color},
                    connectgaps=True
                ),
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["Ask"],
                    mode="lines",
                    name="Ask Price",
                    line={"color": ask_color},
                    connectgaps=True
                ),
            ],
            "layout": go.Layout(
                xaxis={
                    "title": "Timestamp",
                    "color": text_color,
                    "gridcolor": grid_color,
                    "linecolor": grid_color,
                    "zerolinecolor": grid_color,
                },
                yaxis={
                    "title": "",
                    "color": text_color,
                    "gridcolor": grid_color,
                    "linecolor": grid_color,
                    "zerolinecolor": grid_color,
                    "tickfont": {"size": 8, "color": text_color},
                    "tickformat": ".5f",
                    "showgrid": True,
                    "gridwidth": 1,
                },
                title={
                    "text": "EUR/USD Bid and Ask Prices",
                    "font": {"color": text_color},
                },
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
                plot_bgcolor=plot_bg_color,
                paper_bgcolor=dark_bg_color,
                font={"color": text_color},
                legend={"font": {"color": text_color}},
                height=300,
            ),
        }

        spread_figure = {
            "data": [
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["Spread"],
                    mode="lines",
                    name="Spread",
                    line={"color": spread_color},
                    fill="tozeroy",
                    fillcolor=spread_fill_color,
                    connectgaps=True
                ),
            ],
            "layout": go.Layout(
                xaxis={
                    "title": "Timestamp",
                    "color": text_color,
                    "gridcolor": grid_color,
                    "linecolor": grid_color,
                    "zerolinecolor": grid_color,
                },
                yaxis={
                    "title": "Spread (pips)",
                    "color": text_color,
                    "gridcolor": grid_color,
                    "linecolor": grid_color,
                    "zerolinecolor": grid_color,
                },
                title={
                    "text": "EUR/USD Spread",
                    "font": {"color": text_color},
                },
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
                plot_bgcolor=plot_bg_color,
                paper_bgcolor=dark_bg_color,
                font={"color": text_color},
                height=300,
            ),
        }

        stats = html.Div([], style={"display": "none"})

        sma_figure = {
            "data": [
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["Bid"],
                    mode="lines",
                    name="Price",
                    line={"color": price_color},
                    connectgaps=True
                ),
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["SMA_50"],
                    mode="lines",
                    name="SMA 50",
                    line={"color": sma_50_color},
                    connectgaps=True
                ),
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["SMA_200"],
                    mode="lines",
                    name="SMA 200",
                    line={"color": sma_200_color},
                    connectgaps=True
                ),
                go.Scatter(
                    x=df[df["buy_signal"] == True]["Timestamp"],
                    y=df[df["buy_signal"] == True]["Bid"],
                    mode="markers",
                    name="Buy Signal",
                    marker=dict(
                        color="#00ff00",
                        size=10,
                        symbol="triangle-up",
                        line=dict(color="white", width=1)
                    )
                ),
                go.Scatter(
                    x=df[df["sell_signal"] == True]["Timestamp"],
                    y=df[df["sell_signal"] == True]["Bid"],
                    mode="markers",
                    name="Sell Signal",
                    marker=dict(
                        color="#ff0000",
                        size=10,
                        symbol="triangle-down",
                        line=dict(color="white", width=1)
                    )
                ),
                go.Scatter(
                    x=df[df["profit_booking_signal"]]["Timestamp"],
                    y=df[df["profit_booking_signal"]]["Bid"],
                    mode="markers",
                    name="Profit Booking",
                    marker={
                        "symbol": "triangle-up",
                        "size": 15,
                        "color": "#00ff00",
                        "line": {"width": 2, "color": "white"}
                    }
                ),
                go.Scatter(
                    x=df[df["stop_loss_signal"]]["Timestamp"],
                    y=df[df["stop_loss_signal"]]["Bid"],
                    mode="markers",
                    name="Stop Loss",
                    marker={
                        "symbol": "triangle-down",
                        "size": 15,
                        "color": "#ff0000",
                        "line": {"width": 2, "color": "white"}
                    }
                ),
            ],
            "layout": go.Layout(
                xaxis={
                    "title": "Timestamp",
                    "color": text_color,
                    "gridcolor": grid_color,
                    "linecolor": grid_color,
                    "zerolinecolor": grid_color,
                },
                yaxis={
                    "title": "",
                    "color": text_color,
                    "gridcolor": grid_color,
                    "linecolor": grid_color,
                    "zerolinecolor": grid_color,
                    "tickfont": {"size": 8, "color": text_color},
                    "tickformat": ".5f",
                    "showgrid": True,
                    "gridwidth": 1,
                },
                title={
                    "text": "EUR/USD Price with SMA 50 and SMA 200",
                    "font": {"color": text_color},
                },
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
                plot_bgcolor=plot_bg_color,
                paper_bgcolor=dark_bg_color,
                font={"color": text_color},
                legend={"font": {"color": text_color}},
                height=300,
            ),
        }
        
        return bid_ask_figure, spread_figure, sma_figure, stats