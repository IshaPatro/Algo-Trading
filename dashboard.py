import datetime
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import config
import priceCharts
import historyCharts

def create_app():
    app = dash.Dash(__name__)
    
    # Set the background color for the entire page
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
    
    app.layout = html.Div(
        style={
            "backgroundColor": "#1e1e1e",
            "color": "#ffffff",
            "height": "100vh",
            "padding": "20px",
            "fontFamily": "Arial, sans-serif"
        },
        children=[
            html.H1("Trading Dashboard", style={"textAlign": "center", "marginBottom": "30px"}),
            
            priceCharts.create_price_charts_layout(),
            
            html.Div(
                style={
                    "backgroundColor": "#2c2c2c",
                    "padding": "30px",
                    "borderRadius": "8px",
                    "width": "95%",
                    "height": "80px",
                    "textAlign": "center",
                    "marginBottom": "20px"
                },
                children=[
                    html.H3("Total P&L", style={"margin": "0", "fontSize": "20px"}),
                    html.H2(id="total-pnl", style={"margin": "15px 0", "fontSize": "36px"})
                ]
            ),
            
            html.Div(
                style={
                    "backgroundColor": "#2c2c2c",
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
                    "backgroundColor": "#2c2c2c",
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
            
            dcc.Store(id="orders-store", data=[]),
            dcc.Store(id="metrics-store", data=config.trading_metrics),
            dcc.Store(id="orderbook-store", data=initial_orderbook),
            
            dcc.Interval(id="interval-component", interval=500, n_intervals=0),
            historyCharts.create_historical_chart_layout()
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
        ],
        Input("interval-component", "n_intervals"),
        [
            State("orders-store", "data"),
            State("metrics-store", "data"),
            State("orderbook-store", "data")
        ]
    )
    def update_dashboard(n, stored_orders, stored_metrics, stored_orderbook):
        new_orders = list(stored_orders)
        orders_updated = False
        
        while not config.orders_queue.empty():
            new_order = config.orders_queue.get()
            new_orders.append(new_order)
            orders_updated = True
            print(f"New order received: {new_order}")
        
        updated_metrics = dict(stored_metrics) if stored_metrics else {"total_pnl": 0}
        while not config.metrics_queue.empty():
            metrics_update = config.metrics_queue.get()
            updated_metrics.update(metrics_update)
            print(f"Metrics updated: {metrics_update}")
        latest_orderbook = dict(stored_orderbook)
        orderbook_updated = False
        
        while not config.orderbook_queue.empty():
            new_book = config.orderbook_queue.get()
            if new_book.get("bids") or new_book.get("asks"):
                latest_orderbook = {
                    "bids": new_book.get("bids", []),
                    "asks": new_book.get("asks", []),
                    "timestamp": new_book.get("timestamp", datetime.datetime.now())
                }
                orderbook_updated = True
                print(f"Orderbook updated with {len(latest_orderbook['bids'])} bids and {len(latest_orderbook['asks'])} asks")
        
        orders_table = create_orders_table(new_orders)
        orderbook_table = create_orderbook_table(latest_orderbook)
        total_pnl_styled = create_pnl_display(updated_metrics)
        
        return orders_table, orderbook_table, new_orders, updated_metrics, latest_orderbook, total_pnl_styled
    
    priceCharts.register_callbacks(app)
    
    return app

def create_orders_table(orders):
    if not orders:
        # Show placeholder when no orders
        return html.Div([
            html.P("No orders yet", style={"color": "#888888", "textAlign": "center", "padding": "20px"}),
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
            html.Tbody(
                children=[
                    html.Tr(
                        style={"borderBottom": "1px solid #333"},
                        children=[
                            html.Td(order.get("order_id", "N/A"), style={"padding": "8px"}),
                            html.Td(order.get("timestamp", "N/A"), style={"padding": "8px"}),
                            html.Td(
                                order.get("type", "N/A"), 
                                style={
                                    "padding": "8px", 
                                    "color": "green" if order.get("type") == "BUY" else "red"
                                }
                            ),
                            html.Td(f"{float(order.get('price', 0)):.5f}", style={"padding": "8px", "textAlign": "right"}),
                            html.Td(order.get("quantity", "N/A"), style={"padding": "8px", "textAlign": "right"}),
                            html.Td(order.get("strategy", "N/A"), style={"padding": "8px"}),
                        ]
                    ) 
                    for order in reversed(orders)
                ]
            )
        ]
    )

def create_orderbook_table(orderbook):
    if not orderbook or (not orderbook.get("bids") and not orderbook.get("asks")):
        return html.Div([
            html.P("Waiting for orderbook data...", style={"color": "#888888", "textAlign": "center", "padding": "20px"}),
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
                    style={"padding": "8px", "textAlign": "right", "color": "green"}
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
                    style={"padding": "8px", "textAlign": "right", "color": "red"}
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
    pnl_color = "green" if pnl_value >= 0 else "red"
    
    return html.Span(
        total_pnl_display, 
        style={"color": pnl_color}
    )