import datetime
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import config
import priceCharts
import historyCharts
from historyCharts import get_historical_data
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import plotly.graph_objs as go
import warnings
import predict
from predict import predict_today_price, fetch_stock_data
from historyCharts import get_historical_data
from colors import *
from orderHistory import load_orders, save_orders
from metricsManager import initialize_metrics_from_history

warnings.filterwarnings('ignore')

def create_app():
    app = dash.Dash(__name__)
    
    app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <style>
                html, body {
                    background-color: rgb(30,30,30);
                    margin: 0;
                    padding: 0;
                    height: 100%;
                    width: 100%;
                }
            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''
    
    initial_orderbook = {
        "bids": [{"price": "0.00000", "liquidity": "0"}],
        "asks": [{"price": "0.00000", "liquidity": "0"}],
        "timestamp": datetime.datetime.now()
    }
    
    config.orderbook_queue.put(initial_orderbook)
    
    loaded_orders = load_orders()
    config.orders_history = loaded_orders
    
    initialize_metrics_from_history()
    
    priceCharts.initialize_data_thread()
    
    try:
        stock_data = fetch_stock_data()
        prediction_data = prepare_prediction_data(stock_data)
        today_predicted_price = predict_today_price(prediction_data)
    except Exception as e:
        print(f"Error preparing prediction data: {e}")
        prediction_data = pd.DataFrame()
        today_predicted_price = 1.0800
    
    app.layout = html.Div(
        style={
            "backgroundColor": dark_bg_color,
            "color": text_color,
            "height": "100vh",
            "padding": "20px",
            "fontFamily": "Arial, sans-serif"
        },
        children=[
            html.H1("TradePulse", style={"textAlign": "center", "marginBottom": "30px"}),
            html.H4("SMA-Based Algo Trading on OANDA", style={"textAlign": "center", "marginBottom": "30px"}),
            
            priceCharts.create_price_charts_layout(),
            
            html.Div(
                style={
                    "backgroundColor": plot_bg_color,
                    "padding": "20px",
                    "borderRadius": "8px",
                    "marginBottom": "20px",
                    "display": "flex",
                    "justifyContent": "space-between"
                },
                children=[
                    html.Div(
                        style={
                            "textAlign": "center",
                            "flex": "1",
                            "padding": "10px"
                        },
                        children=[
                            html.H3("Buy Avg Price", style={"margin": "0", "fontSize": "18px"}),
                            html.H2(id="buy-avg-price", style={"margin": "10px 0", "fontSize": "24px", "color": buy_color})
                        ]
                    ),
                    html.Div(
                        style={
                            "textAlign": "center",
                            "flex": "1",
                            "padding": "10px"
                        },
                        children=[
                            html.H3("Total P&L", style={"margin": "0", "fontSize": "20px"}),
                            html.H2(id="total-pnl", style={"margin": "10px 0", "fontSize": "32px"})
                        ]
                    ),
                    html.Div(
                        style={
                            "textAlign": "center",
                            "flex": "1",
                            "padding": "10px"
                        },
                        children=[
                            html.H3("Sell Avg Price", style={"margin": "0", "fontSize": "18px"}),
                            html.H2(id="sell-avg-price", style={"margin": "10px 0", "fontSize": "24px", "color": sell_color})
                        ]
                    )
                ]
            ),           
            
            html.Div(
                style={
                    "backgroundColor": plot_bg_color,
                    "padding": "20px",
                    "borderRadius": "8px",
                    "marginBottom": "20px"
                },
                children=[
                    html.H2("Orderbook", style={"marginTop": "0", "marginBottom": "15px"}),
                    html.Div(id="orderbook-table")
                ]
            ),
            
            html.Div(
                style={
                    "backgroundColor": plot_bg_color,
                    "padding": "20px",
                    "borderRadius": "8px",
                    "marginBottom": "20px",
                    "maxHeight": "300px",
                    "overflowY": "auto"
                },
                children=[
                    html.H2("Order History", style={"marginTop": "0", "marginBottom": "15px"}),
                    html.Div(id="orders-table")
                ]
            ),
            
            dcc.Store(id="orders-store", data=load_orders()),
            dcc.Store(id="metrics-store", data=config.trading_metrics),
            dcc.Store(id="orderbook-store", data=initial_orderbook),
            
            dcc.Interval(id="interval-component", interval=2000, n_intervals=0),
            historyCharts.create_historical_chart_layout(),
            html.Div(
                style={
                    "backgroundColor": plot_bg_color,
                    "padding": "20px",
                    "borderRadius": "8px",
                    "marginBottom": "20px"
                },
                children=[
                    html.H2("EUR/USD Price Prediction", style={"marginTop": "0", "marginBottom": "15px"}),
                    html.H3(f"Today's predicted price: ${today_predicted_price:.4f}", 
                        style={'textAlign': 'center', 'color': text_color, 'marginTop': '15px'}),
                    predict.create_prediction_graph(prediction_data, today_predicted_price) if not prediction_data.empty else 
                    html.Div("Prediction data not available", style={"color": inactive_text_color, "textAlign": "center", "padding": "20px"})
                ]
            ),
        ]
    )
    
    @app.callback(
        [
            Output("orders-table", "children"),
            Output("orderbook-table", "children"),
            Output("orders-store", "data"),
            Output("metrics-store", "data"),
            Output("orderbook-store", "data"),
            Output("total-pnl", "children"),
            Output("buy-avg-price", "children"),
            Output("sell-avg-price", "children"),
        ],
        [Input("interval-component", "n_intervals")],
        [State("orders-store", "data"), State("metrics-store", "data"), State("orderbook-store", "data")]
    )
    def update_metrics(n, orders_data, metrics_data, orderbook_data):
        ctx = dash.callback_context
        
        if not ctx.triggered:
            return dash.no_update
        
        try:
            if not config.orders_queue.empty():
                new_order = config.orders_queue.get()
                if new_order not in orders_data:
                    orders_data.append(new_order)
            
            if not config.metrics_queue.empty():
                metrics_data = config.metrics_queue.get()
            
            if not config.orderbook_queue.empty():
                orderbook_data = config.orderbook_queue.get()
            
            orders_table = create_orders_table(orders_data)
            orderbook_table = create_orderbook_table(orderbook_data)
            
            total_pnl = f"${metrics_data['total_pnl']:.2f}"
            buy_avg_price = f"${metrics_data['buy_avg_price']:.5f}"
            sell_avg_price = f"${metrics_data['sell_avg_price']:.5f}"
            
            return orders_table, orderbook_table, orders_data, metrics_data, orderbook_data, total_pnl, buy_avg_price, sell_avg_price
            
        except Exception as e:
            print(f"Error updating metrics: {e}")
            return dash.no_update
    
    return app

def create_orders_table(orders):
    if not orders:
        return html.Div("No orders yet", style={"color": inactive_text_color, "textAlign": "center", "padding": "20px"})
    
    header = html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": "1fr 1fr 1fr 1fr 1fr",
            "borderBottom": f"1px solid {border_color}",
            "padding": "10px 0",
            "fontWeight": "bold"
        },
        children=[
            html.Div("Time", style={"textAlign": "left"}),
            html.Div("Type", style={"textAlign": "center"}),
            html.Div("Quantity", style={"textAlign": "right"}),
            html.Div("Price", style={"textAlign": "right"}),
            html.Div("Strategy", style={"textAlign": "center"})
        ]
    )
    
    rows = []
    for order in reversed(orders):
        try:
            order_time = datetime.datetime.fromisoformat(order["timestamp"]).strftime("%H:%M:%S")
            order_type = order["type"]
            quantity = order["quantity"]
            price = float(order["price"])
            strategy = order.get("strategy", "")
            
            type_color = buy_color if order_type == "BUY" else sell_color
            
            row = html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr 1fr 1fr 1fr",
                    "borderBottom": f"1px solid {border_color}",
                    "padding": "8px 0"
                },
                children=[
                    html.Div(order_time, style={"textAlign": "left"}),
                    html.Div(order_type, style={"textAlign": "center", "color": type_color, "fontWeight": "bold"}),
                    html.Div(f"{quantity:,}", style={"textAlign": "right"}),
                    html.Div(f"${price:.5f}", style={"textAlign": "right"}),
                    html.Div(strategy, style={"textAlign": "center"})
                ]
            )
            rows.append(row)
        except Exception as e:
            print(f"Error rendering order row: {e}")
    
    return html.Div([header, html.Div(rows)])

def create_orderbook_table(orderbook):
    if not orderbook or "bids" not in orderbook or "asks" not in orderbook:
        return html.Div("Orderbook data not available", style={"color": inactive_text_color, "textAlign": "center", "padding": "20px"})
    
    bids = orderbook["bids"][:5] if len(orderbook["bids"]) > 5 else orderbook["bids"]
    asks = orderbook["asks"][:5] if len(orderbook["asks"]) > 5 else orderbook["asks"]
    
    asks = list(reversed(asks))
    
    rows = []
    
    for ask in asks:
        price = float(ask["price"])
        liquidity = int(ask["liquidity"]) if "liquidity" in ask else 0
        
        row = html.Div(
            style={
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "padding": "5px 0"
            },
            children=[
                html.Div(f"${price:.5f}", style={"textAlign": "right", "color": sell_color, "fontWeight": "bold"}),
                html.Div(f"{liquidity:,}", style={"textAlign": "right", "paddingLeft": "20px"})
            ]
        )
        rows.append(row)
    
    header = html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": "1fr 1fr",
            "borderBottom": f"1px solid {border_color}",
            "borderTop": f"1px solid {border_color}",
            "padding": "8px 0",
            "fontWeight": "bold"
        },
        children=[
            html.Div("Price", style={"textAlign": "right"}),
            html.Div("Liquidity