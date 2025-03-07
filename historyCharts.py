import pandas as pd
import plotly.graph_objs as go
import tpqoa
import config
from dash import dcc, html

dark_bg_color = "#1e1e1e"
text_color = "#ffffff" 
grid_color = "#4d4d4d" 
plot_bg_color = "#2d2d2d" 

def get_historical_data(instrument="EUR_USD", start="2024-01-01", end="2025-03-03", granularity="D", price="B"):
    """Fetch historical price data from OANDA using tpqoa"""
    try:
        api = tpqoa.tpqoa("oanda.cfg")
        historical_df = api.get_history(
            instrument=instrument,
            start=start,
            end=end,
            granularity=granularity,
            price=price
        )
        historical_df["time"] = historical_df.index
        return historical_df
    except Exception as e:
        print(f"Error fetching historical data: {e}")
        return pd.DataFrame()

def create_historical_chart():
    """Create a candlestick chart with historical data"""
    try:
        historical_df = get_historical_data(instrument=config.instrument)
        
        if historical_df.empty:
            return html.Div("Error loading historical data", 
                          style={"color": text_color, "textAlign": "center", "padding": "20px"})
        
        fig_historical = go.Figure()
        fig_historical.add_trace(go.Candlestick(
            x=historical_df["time"],
            open=historical_df["o"],
            high=historical_df["h"],
            low=historical_df["l"],
            close=historical_df["c"],
            increasing_line_color='#00ff00',
            decreasing_line_color='#ff0000',
            name="Candlestick"
        ))

        fig_historical.update_layout(
            title="EUR/USD Historical Prices",
            xaxis_title="Date",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False,
            plot_bgcolor=plot_bg_color,
            paper_bgcolor=dark_bg_color,
            font=dict(color=text_color),
            xaxis={
                "title": "Date",
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
            height=400
        )
        
        return dcc.Graph(
            id="historical-graph",
            figure=fig_historical,
            style={
                "backgroundColor": plot_bg_color,
                "border": "1px solid #4d4d4d",
                "borderRadius": "5px",
                "margin": "10px",
            }
        )
    except Exception as e:
        print(f"Error creating historical chart: {e}")
        return html.Div(f"Error creating historical chart: {str(e)}", 
                      style={"color": text_color, "textAlign": "center", "padding": "20px"})

def create_historical_chart_layout():
    """Create the layout for the historical chart section"""
    return html.Div([
        html.H2("Historical Data", style={"marginTop": "20px", "marginBottom": "15px", "color": text_color}),
        create_historical_chart()
    ], style={
        "backgroundColor": plot_bg_color,
        "padding": "15px",
        "borderRadius": "8px",
        "marginBottom": "20px"
    })