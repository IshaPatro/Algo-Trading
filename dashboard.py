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
            
            dcc.Store(id="orders-store", data=config.orders_history),
            dcc.Store(id="metrics-store", data=config.trading_metrics),
            dcc.Store(id="orderbook-store", data=initial_orderbook),
            
            dcc.Interval(id="interval-component", interval=500, n_intervals=0),
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
        Input("interval-component", "n_intervals"),
        [
            State("orders-store", "data"),
            State("metrics-store", "data"),
            State("orderbook-store", "data")
        ]
    )
    def update_dashboard(n, stored_orders, stored_metrics, stored_orderbook):
        new_orders = list(stored_orders) if stored_orders else []
        orders_updated = False
        while not config.orders_queue.empty():
            try:
                new_order = config.orders_queue.get()
                if new_order and isinstance(new_order, dict):
                    new_orders.append(new_order)
                    # Add to config.orders_history for persistence
                    if new_order not in config.orders_history:
                        config.orders_history.append(new_order)
                    orders_updated = True
                    print(f"New order received and added to display: {new_order}")
            except Exception as e:
                print(f"Error processing order from queue: {e}")
        
        with config.data_lock:
            updated_metrics = config.trading_metrics.copy()
        
        while not config.metrics_queue.empty():
            try:
                metrics_update = config.metrics_queue.get()
                if metrics_update and isinstance(metrics_update, dict):
                    updated_metrics.update(metrics_update)
                    print(f"Metrics updated: {metrics_update}")
            except Exception as e:
                print(f"Error processing metrics from queue: {e}")
                
        latest_orderbook = dict(stored_orderbook) if stored_orderbook else {"bids": [], "asks": [], "timestamp": datetime.datetime.now()}
        orderbook_updated = False
        
        while not config.orderbook_queue.empty():
            try:
                new_book = config.orderbook_queue.get()
                if new_book and (new_book.get("bids") or new_book.get("asks")):
                    latest_orderbook = {
                        "bids": new_book.get("bids", []),
                        "asks": new_book.get("asks", []),
                        "timestamp": new_book.get("timestamp", datetime.datetime.now())
                    }
                    orderbook_updated = True
            except Exception as e:
                print(f"Error processing orderbook from queue: {e}")
                
        orders_table = create_orders_table(new_orders)
        orderbook_table = create_orderbook_table(latest_orderbook)
        total_pnl_styled = create_pnl_display(updated_metrics)
        
        buy_avg_price = updated_metrics.get('buy_avg_price', 0)
        buy_avg_display = f"{buy_avg_price:.5f}" if updated_metrics.get('total_buy_quantity', 0) > 0 else "N/A"
        
        sell_avg_price = updated_metrics.get('sell_avg_price', 0)
        sell_avg_display = f"{sell_avg_price:.5f}" if updated_metrics.get('total_sell_quantity', 0) > 0 else "N/A"
        
        return orders_table, orderbook_table, new_orders, updated_metrics, latest_orderbook, total_pnl_styled, buy_avg_display, sell_avg_display
    
    priceCharts.register_callbacks(app)
    
    return app


        
#     except Exception as e:
#         print(f"Error in fetch_stock_data: {e}")
#         raise

def prepare_prediction_data(df):
    SMA50 = pd.DataFrame()
    SMA50['Price'] = df['Close'].rolling(window=50).mean()
    SMA200 = pd.DataFrame()
    SMA200['Price'] = df['Close'].rolling(window=200).mean()

    Data = pd.DataFrame()
    Data['Price'] = df['Close']
    Data['SMA50'] = SMA50['Price']
    Data['SMA200'] = SMA200['Price']
    Data['funds'] = 100000 
    
    buy_sell = buy_sell_signal(Data)
    Data['Buy_price'] = buy_sell[0]
    Data['Sell_price'] = buy_sell[1]
    Data['Open_pos'] = buy_sell[2]
    Data['live_pos'] = Data['Open_pos'].multiply(Data['Price'])
    Data['funds'] = buy_sell[3]
    
    return Data

def buy_sell_signal(data):
    buy_signal = []
    sell_signal = []
    open_position = []
    funds = [100000] * len(data)
    last_funds = 100000
    flag = 0

    for i in range(len(data)):
        if data['SMA50'][i] > data['SMA200'][i]:
            if flag == 0:
                flag = 1
                buy_signal.append(data['Price'][i])
                last_pos = last_funds / data['Price'][i]
                funds[i] = last_funds
                open_position.append(last_pos)
                sell_signal.append(np.nan)
            else:
                buy_signal.append(np.nan)
                last_funds = data['Price'][i] * last_pos
                funds[i] = last_funds
                open_position.append(last_pos)
                sell_signal.append(np.nan)
        elif data['SMA50'][i] < data['SMA200'][i]:
            if flag == 1:
                flag = 0
                buy_signal.append(np.nan)
                last_funds = last_pos * data['Price'][i]
                funds[i] = last_funds
                open_position.append(0)
                sell_signal.append(data['Price'][i])
            else:
                buy_signal.append(np.nan)
                funds[i] = last_funds
                open_position.append(0)
                sell_signal.append(np.nan)
        else:
            buy_signal.append(np.nan)
            open_position.append(0)
            sell_signal.append(np.nan)
    return buy_signal, sell_signal, open_position, funds, flag

def create_orders_table(orders):
    if not orders:
        return html.Div([
            html.P("No orders yet", style={"color": inactive_text_color, "textAlign": "center", "padding": "20px"}),
            html.Table(
                style={"width": "100%", "borderCollapse": "collapse"},
                children=[
                    html.Thead(
                        style={"borderBottom": "2px solid #444"},
                        children=[
                            html.Tr([
                                html.Th("Order ID", style={"padding": "10px", "textAlign": "left"}),
                                html.Th("Timestamp", style={"padding": "10px", "textAlign": "left"}),
                                html.Th("Type", style={"padding": "10px", "textAlign": "left"}),
                                html.Th("Price", style={"padding": "10px", "textAlign": "right"}),
                                html.Th("Quantity", style={"padding": "10px", "textAlign": "right"}),
                                html.Th("Strategy", style={"padding": "10px", "textAlign": "left"}),
                            ])
                        ]
                    ),
                    html.Tbody()
                ]
            )
        ])
    
    order_rows = []
    for order in reversed(orders):
        try:
            order_rows.append(
                html.Tr(
                    style={"borderBottom": "1px solid #333"},
                    children=[
                        html.Td(str(order.get("order_id", "N/A")), style={"padding": "8px"}),
                        html.Td(str(order.get("timestamp", "N/A")), style={"padding": "8px"}),
                        html.Td(
                            str(order.get("type", "N/A")), 
                            style={
                                "padding": "8px", 
                                "color": buy_color if order.get("type") == "BUY" else sell_color
                            }
                        ),
                        html.Td(f"{float(order.get('price', 0)):.5f}", style={"padding": "8px", "textAlign": "right"}),
                        html.Td(f"{int(float(order.get('quantity', 0)))}", style={"padding": "8px", "textAlign": "right"}),
                        html.Td(str(order.get("strategy", "N/A")), style={"padding": "8px"}),
                    ]
                )
            )
        except Exception as e:
            print(f"Error creating order row: {e}, Order: {order}")
    
    return html.Table(
        style={"width": "100%", "borderCollapse": "collapse"},
        children=[
            html.Thead(
                style={"borderBottom": "2px solid #444"},
                children=[
                    html.Tr([
                        html.Th("Order ID", style={"padding": "10px", "textAlign": "left"}),
                        html.Th("Timestamp", style={"padding": "10px", "textAlign": "left"}),
                        html.Th("Type", style={"padding": "10px", "textAlign": "left"}),
                        html.Th("Price", style={"padding": "10px", "textAlign": "right"}),
                        html.Th("Quantity", style={"padding": "10px", "textAlign": "right"}),
                        html.Th("Strategy", style={"padding": "10px", "textAlign": "left"}),
                    ])
                ]
            ),
            html.Tbody(children=order_rows)
        ]
    )

def create_orderbook_table(orderbook):
    if not orderbook or (not orderbook.get("bids") and not orderbook.get("asks")):
        return html.Div([
            html.P("Waiting for orderbook data...", style={"color": inactive_text_color, "textAlign": "center", "padding": "20px"}),
            html.Table(
                style={"width": "100%", "borderCollapse": "collapse"},
                children=[
                    html.Thead(
                        style={"borderBottom": "2px solid #444"},
                        children=[
                            html.Tr([
                                html.Th("Bid Price", style={"padding": "10px", "textAlign": "right", "width": "25%"}),
                                html.Th("Bid Liquidity", style={"padding": "10px", "textAlign": "right", "width": "25%"}),
                                html.Th("Ask Price", style={"padding": "10px", "textAlign": "right", "width": "25%"}),
                                html.Th("Ask Liquidity", style={"padding": "10px", "textAlign": "right", "width": "25%"}),
                            ])
                        ]
                    ),
                    html.Tbody()
                ]
            )
        ])
    
    timestamp_str = orderbook.get("timestamp", "")
    if isinstance(timestamp_str, datetime.datetime):
        timestamp_str = timestamp_str.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    bids = orderbook.get("bids", [])
    asks = orderbook.get("asks", [])
    max_rows = max(len(bids), len(asks), 1)
    
    orderbook_rows = []
    for i in range(max_rows):
        row_cells = []
        
        if i < len(bids):
            try:
                bid_price = float(bids[i]['price'])
                price_display = f"{bid_price:.5f}"
            except (ValueError, KeyError):
                price_display = "N/A"
            
            row_cells.append(
                html.Td(
                    price_display, 
                    style={"padding": "8px", "textAlign": "right", "color": buy_color}
                )
            )
        else:
            row_cells.append(html.Td("", style={"padding": "8px"}))
        
        if i < len(bids):
            row_cells.append(
                html.Td(
                    bids[i].get('liquidity', 'N/A'), 
                    style={"padding": "8px", "textAlign": "right"}
                )
            )
        else:
            row_cells.append(html.Td("", style={"padding": "8px"}))
        
        if i < len(asks):
            try:
                ask_price = float(asks[i]['price'])
                price_display = f"{ask_price:.5f}"
            except (ValueError, KeyError):
                price_display = "N/A"
            
            row_cells.append(
                html.Td(
                    price_display, 
                    style={"padding": "8px", "textAlign": "right", "color": sell_color}
                )
            )
        else:
            row_cells.append(html.Td("", style={"padding": "8px"}))
        
        if i < len(asks):
            row_cells.append(
                html.Td(
                    asks[i].get('liquidity', 'N/A'), 
                    style={"padding": "8px", "textAlign": "right"}
                )
            )
        else:
            row_cells.append(html.Td("", style={"padding": "8px"}))
        
        orderbook_rows.append(html.Tr(
            style={"borderBottom": "1px solid #333"},
            children=row_cells
        ))
    
    return html.Table(
        style={"width": "100%", "borderCollapse": "collapse"},
        children=[
            html.Thead(
                style={"borderBottom": "2px solid #444"},
                children=[
                    html.Tr([
                        html.Th("Bid Price", style={"padding": "10px", "textAlign": "right", "width": "25%"}),
                        html.Th("Bid Liquidity", style={"padding": "10px", "textAlign": "right", "width": "25%"}),
                        html.Th("Ask Price", style={"padding": "10px", "textAlign": "right", "width": "25%"}),
                        html.Th("Ask Liquidity", style={"padding": "10px", "textAlign": "right", "width": "25%"}),
                    ])
                ]
            ),
            html.Tbody(
                children=orderbook_rows
            )
        ]
    )

def create_pnl_display(metrics):
    pnl_value = metrics.get('total_pnl', 0)
    total_pnl_display = f"${pnl_value:.2f}"
    pnl_color = buy_color if pnl_value >= 0 else sell_color
    
    return html.Span(
        total_pnl_display, 
        style={"color": pnl_color}
    )