import pandas as pd
import plotly.graph_objs as go
import tpqoa
import config
from dash import dcc, html
from oandapyV20.endpoints.instruments import InstrumentsCandles
from colors import *

def get_historical_data(instrument="EUR_USD", start="2024-01-01", end="2025-03-03", granularity="D", price="B"):
    try:
        params = {
            "from": start,
            "to": end,
            "granularity": granularity,
            "price": price
        }

        r = InstrumentsCandles(instrument=instrument, params=params)
        response = config.client.request(r)
        candles = response.get("candles", [])
        data = []

        for candle in candles:
            row = {
                "time": candle["time"],
                "volume": candle["volume"],
                "complete": candle["complete"]
            }
            for price_type in ["bid", "ask", "mid"]:
                if price_type in candle:
                    for key, value in candle[price_type].items():
                        row[f"{price_type}_{key}"] = float(value)
            data.append(row)

        historical_df = pd.DataFrame(data)
        historical_df["time"] = pd.to_datetime(historical_df["time"])
        print("Historical DF: ", historical_df.columns)
        return historical_df

    except Exception as e:
        print(f"Error fetching historical data: {e}")
        return pd.DataFrame()
    
def create_historical_chart():
    try:
        historical_df = get_historical_data(instrument=config.instrument)
        
        if historical_df.empty:
            return html.Div("Error loading historical data", 
                          style={"color": text_color, "textAlign": "center", "padding": "20px"})
        
        fig_historical = go.Figure()
        fig_historical.add_trace(go.Candlestick(
            x=historical_df["time"],
            open=historical_df["bid_o"],
            high=historical_df["bid_h"],
            low=historical_df["bid_l"],
            close=historical_df["bid_c"],
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
    return html.Div([
        html.H2("Historical Data", style={"marginTop": "20px", "marginBottom": "15px", "color": text_color}),
        create_historical_chart()
    ], style={
        "backgroundColor": plot_bg_color,
        "padding": "15px",
        "borderRadius": "8px",
        "marginBottom": "20px"
    })