import time
import datetime
import pandas as pd
import plotly.graph_objs as go
from dash import dcc, html
from dash.dependencies import Input, Output
import config
from threading import Thread, Event

# Style variables
dark_bg_color = "#1e1e1e"
plot_bg_color = "#2c2c2c"
text_color = "#ffffff"
grid_color = "#444444"

# Data storage
data = []
stop_event = Event()

def stream_data(stop_event):
    start_time = time.time()
    while not stop_event.is_set():
        if time.time() - start_time > 300:
            stop_event.set()
            break
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
                dcc.Graph(id="volatility-graph"),
            ], style={"width": "50%", "display": "inline-block"}),
            
            html.Div([
                dcc.Graph(id="histogram-graph"),
            ], style={"width": "50%", "display": "inline-block"}),
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
         Output("volatility-graph", "figure"),
         Output("histogram-graph", "figure"),
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
            return empty_figure, empty_figure, empty_figure, empty_figure, empty_stats
        
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        
        # Calculate additional metrics
        if len(df) > 1:
            df["Price_Change"] = df["Bid"].diff().fillna(0)
            df["Volatility"] = df["Price_Change"].rolling(window=10).std().fillna(0) * 10000
        else:
            df["Price_Change"] = 0
            df["Volatility"] = 0

        # Bid-ask figure
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
                    "title": "Price",
                    "color": text_color,
                    "gridcolor": grid_color,
                    "linecolor": grid_color,
                    "zerolinecolor": grid_color,
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

        # Spread figure
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

        # Volatility figure
        volatility_figure = {
            "data": [
                go.Scatter(
                    x=df["Timestamp"],
                    y=df["Volatility"],
                    mode="lines",
                    name="Volatility",
                    line={"color": "#ff9900"},
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
                    "title": "Volatility (pips)",
                    "color": text_color,
                    "gridcolor": grid_color,
                    "linecolor": grid_color,
                    "zerolinecolor": grid_color,
                },
                title={
                    "text": "EUR/USD Volatility (10-period Std. Dev.)",
                    "font": {"color": text_color},
                },
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
                plot_bgcolor=plot_bg_color,
                paper_bgcolor=dark_bg_color,
                font={"color": text_color},
                height=300,
            ),
        }

        # Histogram of spreads
        histogram_figure = {
            "data": [
                go.Histogram(
                    x=df["Spread"],
                    marker_color="#9c27b0",
                    opacity=0.7,
                    name="Spread Distribution",
                    nbinsx=20
                )
            ],
            "layout": go.Layout(
                xaxis={
                    "title": "Spread (pips)",
                    "color": text_color,
                    "gridcolor": grid_color,
                    "linecolor": grid_color,
                    "zerolinecolor": grid_color,
                },
                yaxis={
                    "title": "Frequency",
                    "color": text_color,
                    "gridcolor": grid_color,
                    "linecolor": grid_color,
                    "zerolinecolor": grid_color,
                },
                title={
                    "text": "Spread Distribution",
                    "font": {"color": text_color},
                },
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
                plot_bgcolor=plot_bg_color,
                paper_bgcolor=dark_bg_color,
                font={"color": text_color},
                height=300,
            ),
        }

        # Stats panel
        stats = html.Div([
            html.Div([
                html.Div([
                    html.H4("Current Price", style={"color": text_color, "textAlign": "center", "fontSize": "16px", "margin": "0 0 10px 0"}),
                    html.Table([
                        html.Tr([html.Td("Bid:", style={"padding": "5px 10px"}), 
                                html.Td(f"{df['Bid'].iloc[-1]:.5f}", style={"padding": "5px 10px", "textAlign": "right"})]),
                        html.Tr([html.Td("Ask:", style={"padding": "5px 10px"}), 
                                html.Td(f"{df['Ask'].iloc[-1]:.5f}", style={"padding": "5px 10px", "textAlign": "right"})]),
                        html.Tr([html.Td("Spread:", style={"padding": "5px 10px"}), 
                                html.Td(f"{df['Spread'].iloc[-1]:.1f} pips", style={"padding": "5px 10px", "textAlign": "right"})]),
                    ], style={"width": "100%", "borderCollapse": "collapse"})
                ], style={"width": "50%", "display": "inline-block", "verticalAlign": "top"}),
                
                html.Div([
                    html.H4("Session Stats", style={"color": text_color, "textAlign": "center", "fontSize": "16px", "margin": "0 0 10px 0"}),
                    html.Table([
                        html.Tr([html.Td("Avg Spread:", style={"padding": "5px 10px"}), 
                                html.Td(f"{df['Spread'].mean():.1f} pips", style={"padding": "5px 10px", "textAlign": "right"})]),
                        html.Tr([html.Td("Min Spread:", style={"padding": "5px 10px"}), 
                                html.Td(f"{df['Spread'].min():.1f} pips", style={"padding": "5px 10px", "textAlign": "right"})]),
                        html.Tr([html.Td("Max Spread:", style={"padding": "5px 10px"}), 
                                html.Td(f"{df['Spread'].max():.1f} pips", style={"padding": "5px 10px", "textAlign": "right"})]),
                    ], style={"width": "100%", "borderCollapse": "collapse"})
                ], style={"width": "50%", "display": "inline-block", "verticalAlign": "top"})
            ], style={"display": "flex", "justifyContent": "space-around"})
        ], style={"backgroundColor": dark_bg_color, "padding": "15px", "borderRadius": "5px", "margin": "10px 0"})

        return bid_ask_figure, spread_figure, volatility_figure, histogram_figure, stats