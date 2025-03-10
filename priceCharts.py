import time
import datetime
import pandas as pd
import plotly.graph_objs as go
from dash import dcc, html
from dash.dependencies import Input, Output
import config
from threading import Thread, Event

dark_bg_color = "#1e1e1e"
plot_bg_color = "#2c2c2c"
text_color = "#ffffff"
grid_color = "#444444"

data = []
stop_event = Event()

def stream_data(stop_event):
    while not stop_event.is_set():
        try:
            response = config.client.request(config.r)
            prices = response["prices"]
            for price in prices:
                timestamp = datetime.datetime.now().isoformat()
                bid = float(price["bids"][0]["price"])
                ask = float(price["asks"][0]["price"])
                spread = (ask - bid)*10000
                new_data = {"Timestamp": timestamp, "Bid": bid, "Ask": ask, "Spread": spread}
                data.append(new_data)
        except Exception as e:
            print(f"Error: {e}")
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
        else:
            df["Price_Change"] = 0
            df["Volatility"] = 0
            df["SMA_50"] = df["Bid"]
            df["SMA_200"] = df["Bid"]

        bid_ask_figure = {
            "data": [
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["Bid"],
                    mode="lines",
                    name="Bid Price",
                    line={"color": "#00ff00"},
                    connectgaps=True
                ),
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["Ask"],
                    mode="lines",
                    name="Ask Price",
                    line={"color": "#ff0000"},
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
                    "tickfont": {"size": 8, "color": "#ffffff"},
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
                    line={"color": "#1f77b4"},
                    fill="tozeroy",
                    fillcolor="rgba(31, 119, 180, 0.2)",
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
                    line={"color": "#00ff00"},
                    connectgaps=True
                ),
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["SMA_50"],
                    mode="lines",
                    name="SMA 50",
                    line={"color": "#ffa500"},
                    connectgaps=True
                ),
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["SMA_200"],
                    mode="lines",
                    name="SMA 200",
                    line={"color": "#1f77b4"},
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
                    "tickfont": {"size": 8, "color": "#ffffff"},
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