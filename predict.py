import datetime
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import warnings
import plotly.graph_objs as go
import yfinance as yf
from dash import dcc, html

warnings.filterwarnings('ignore')

def fetch_stock_data():
    stock = "EURUSD=X"
    end_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=5*365)).strftime("%Y-%m-%d")
    
    df = yf.download(stock, start=start_date, end=end_date)
    df.dropna(how='any', inplace=True)
    return df

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
    df_prediction = data.copy()
    df_prediction = df_prediction.reset_index()
    df_prediction['Date_num'] = pd.to_datetime(df_prediction['Date']).map(datetime.datetime.toordinal)
    X = df_prediction['Date_num'].values.reshape(-1, 1)
    y = df_prediction['Price'].values
    model = LinearRegression()
    model.fit(X, y)
    today_date_num = datetime.datetime.now().toordinal()
    predicted_price = model.predict([[today_date_num]])[0]
    return predicted_price

# Define the same color scheme as historyCharts.py
dark_bg_color = "#1e1e1e"
text_color = "#ffffff" 
grid_color = "#4d4d4d" 
plot_bg_color = "#2d2d2d" 

def create_prediction_graph(prediction_data, today_predicted_price):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    figure = {
        'data': [
            go.Scatter(x=prediction_data.index, y=prediction_data['Price'], name='EUR/USD', line=dict(color='purple', width=2)),
            go.Scatter(x=prediction_data.index, y=prediction_data['SMA50'], name='SMA50', line=dict(color='orange', width=1.5)),
            go.Scatter(x=prediction_data.index, y=prediction_data['SMA200'], name='SMA200', line=dict(color='#1E90FF', width=1.5)),
            go.Scatter(x=prediction_data.index, y=prediction_data['Buy_price'], mode='markers', marker=dict(color='green', symbol='triangle-up', size=10), name='Buy Signal'),
            go.Scatter(x=prediction_data.index, y=prediction_data['Sell_price'], mode='markers', marker=dict(color='red', symbol='triangle-down', size=10), name='Sell Signal'),
            go.Scatter(x=[today], y=[today_predicted_price], mode='markers', marker=dict(color='yellow', size=15), name='Today\'s Prediction')
        ],
        'layout': go.Layout(
            title={
                "text": "EUR/USD Price Prediction",
                "font": {"color": text_color}
            },
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
            hovermode='closest',
            plot_bgcolor=plot_bg_color,
            paper_bgcolor=dark_bg_color,
            font=dict(color=text_color),
            legend={"font": {"color": text_color}},
            height=400,
            margin={"l": 40, "r": 40, "t": 40, "b": 40},
            xaxis_rangeslider_visible=False,
            template="plotly_dark"
        )
    }
    
    # Wrap the figure in a dcc.Graph component with the same styling as historyCharts
    return dcc.Graph(
        id="prediction-graph",
        figure=figure,
        style={
            "backgroundColor": dark_bg_color,
            "border": "1px solid #4d4d4d",
            "borderRadius": "5px",
            "margin": "10px",
            "padding": "15px",
        },
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d']
        }
    )