import datetime
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import warnings
import plotly.graph_objs as go
from dash import dcc, html
from oandapyV20 import API
from oandapyV20.endpoints.instruments import InstrumentsCandles
import config
from colors import *

warnings.filterwarnings('ignore')

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
        return historical_df

    except Exception as e:
        print(f"Error fetching historical data: {e}")
        return pd.DataFrame()

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

def predict_today_price(data):
    if data.empty or 'Price' not in data.columns:
        print("Error: Empty data or missing Price column")
        return 1.0800
    
    last_30_days = data.tail(30).copy()
    
    X = np.array(range(len(last_30_days))).reshape(-1, 1)
    y = last_30_days['Price'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    next_day = np.array([[len(last_30_days)]])
    predicted_price = model.predict(next_day)[0]
    
    return predicted_price

def fetch_stock_data():
    
    end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=5*365)).strftime("%Y-%m-%d")
    
    print(f"Attempting to download historical data from {start_date} to {end_date}")
    
    try:
        df = get_historical_data(
            instrument=config.instrument,
            start=start_date,
            end=end_date,
            granularity="D",
            price="M"
        )
        
        print("Historical DF columns:", df.columns.tolist())
        print("Historical DF shape:", df.shape)
        
        if df.empty:
            raise Exception("No historical data available")
        
        prediction_df = pd.DataFrame()
        
        prediction_df['Open'] = df['mid_o'].astype(float)
        prediction_df['High'] = df['mid_h'].astype(float)
        prediction_df['Low'] = df['mid_l'].astype(float)
        prediction_df['Close'] = df['mid_c'].astype(float)
        prediction_df['Volume'] = df['volume'].astype(float)
        prediction_df['Adj Close'] = df['mid_c'].astype(float)
        
        prediction_df.index = pd.to_datetime(df['time'])
        
        prediction_df = prediction_df.sort_index()
        
        if len(prediction_df) < 200:
            raise Exception(f"Not enough data points for prediction: {len(prediction_df)}")
        
        prediction_df.dropna(how='any', inplace=True)
        print(f"Successfully prepared prediction data with {len(prediction_df)} rows")
        
        return prediction_df
        
    except Exception as e:
        print(f"Error in fetch_stock_data: {e}")
        raise


def create_prediction_graph(data, today_prediction):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['Price'],
        mode='lines',
        name='Price',
        line=dict(color=price_color, width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['SMA50'],
        mode='lines',
        name='SMA50',
        line=dict(color=sma_50_color, width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['SMA200'],
        mode='lines',
        name='SMA200',
        line=dict(color=sma_200_color, width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['Buy_price'],
        mode='markers',
        name='Buy Signal',
        marker=dict(color=buy_color, size=8, symbol='triangle-up')
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data['Sell_price'],
        mode='markers',
        name='Sell Signal',
        marker=dict(color=sell_color, size=8, symbol='triangle-down')
    ))
    
    last_date = data.index[-1]
    next_date = last_date + pd.Timedelta(days=1)
    
    fig.add_trace(go.Scatter(
        x=[next_date],
        y=[today_prediction],
        mode='markers',
        name='Prediction',
        marker=dict(color='#FFFF00', size=12, symbol='star')
    ))
    
    fig.update_layout(
        plot_bgcolor=plot_bg_color,
        paper_bgcolor=dark_bg_color,
        font=dict(color=text_color),
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10)
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=grid_color,
            showline=True,
            linecolor=grid_line_color,
            title=None
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=grid_color,
            showline=True,
            linecolor=grid_line_color,
            title=None
        ),
        height=500
    )
    
    return dcc.Graph(
        figure=fig,
        config={'displayModeBar': False},
        style={'height': '100%', 'width': '100%'}
    )