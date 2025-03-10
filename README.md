# TradePulse: Algorithmic Trading Platform

## Overview
TradePulse is a sophisticated algorithmic trading platform that implements SMA-based trading strategies for the forex market, specifically for EUR/USD currency pair on OANDA. The platform features a real-time dashboard for monitoring trades, visualizing price movements, and tracking performance metrics.

## Features

- **Real-time Trading**: Automated trading based on SMA-50 and SMA-200 crossover strategies
- **Technical Indicators**: Implementation of SMA (Simple Moving Average) and RSI (Relative Strength Index)
- **Live Dashboard**: Interactive visualization of price charts, orderbook, and trade history
- **Performance Metrics**: Real-time calculation of P&L, average buy/sell prices
- **Price Prediction**: Machine learning-based price prediction for EUR/USD
- **Order Management**: Automated order placement and tracking

## Architecture

The application is built with a modular architecture:

- **Data Stream**: Real-time price data from OANDA API
- **Trading Logic**: Strategy implementation based on technical indicators
- **Order Management**: Handling order creation and execution
- **Metrics Calculation**: Real-time P&L and performance tracking
- **Dashboard**: Visualization using Dash and Plotly

## Installation

### Prerequisites
- Python 3.13+
- OANDA API access (account ID and access token)

### Setup

1. Clone the repository
   ```
   git clone <repository-url>
   cd Algo-Trading
   ```

2. Create and activate a virtual environment
   ```
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

4. Configure OANDA API credentials
   - Create a file named `oanda.cfg` with the following content:
   ```
   [oanda]
   account_id = YOUR_ACCOUNT_ID
   access_token = YOUR_ACCESS_TOKEN
   account_type = practice  # or 'live' for real trading
   ```

## Usage

### Running the Dashboard

```
python app.py
```

This will start the dashboard on http://localhost:8050

### Components

- **Price Charts**: Real-time visualization of price movements with technical indicators
- **Orderbook Display**: Current market depth and liquidity
- **Order History**: Record of executed trades
- **Performance Metrics**: P&L, average prices, and trading statistics
- **Price Prediction**: ML-based forecast of future prices

## Trading Strategies

### SMA-50 Strategy
- Buy when price crosses above SMA-50
- Sell when price crosses below SMA-50

### Golden/Death Cross Strategy
- Buy on Golden Cross (SMA-50 crosses above SMA-200)
- Sell on Death Cross (SMA-50 crosses below SMA-200)

### Support/Resistance Strategy
- Buy when price bounces off SMA-50 from below
- Sell when price rejects SMA-50 from above

## Deployment

### Local Deployment
Follow the installation and usage instructions above.

### Heroku Deployment
1. Create a Heroku account and install the Heroku CLI
2. Login to Heroku CLI
   ```
   heroku login
   ```
3. Create a new Heroku app
   ```
   heroku create your-app-name
   ```
4. Set environment variables for OANDA credentials
   ```
   heroku config:set account_id=YOUR_ACCOUNT_ID
   heroku config:set access_token=YOUR_ACCESS_TOKEN
   heroku config:set account_type=practice
   ```
5. Deploy the application
   ```
   git push heroku main
   ```

## Testing

The project includes unit tests for metrics calculation and dashboard rendering:

```
python -m unittest test_metrics.py
python -m unittest test_dashboard_rendering.py
```

## License

[MIT License](LICENSE)

## Disclaimer

This software is for educational purposes only. Trading financial instruments carries significant risk. Always use proper risk management and consult with a financial advisor before engaging in real trading.