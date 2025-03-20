from queue import Queue
from threading import Lock
import configparser
import oandapyV20
import oandapyV20.endpoints.pricing as pricing
import os

STRONG_SIGNAL_QUANTITY = 100000
SMA_50_WINDOW = 50
SMA_200_WINDOW = 200
RSI_WINDOW = 14
PROFIT_THRESHOLD_PIPS = 0.0005
LOSS_THRESHOLD_PIPS = 0.0005
PROFIT_BOOKING_QUANTITY = 500000

price_data = []
orders_history = []
orderbook_data = []
data_lock = Lock()

orders_queue = Queue()
metrics_queue = Queue()
orderbook_queue = Queue()

trading_metrics = {
    "total_pnl": 0,
    "total_buy_quantity": 0,
    "total_sell_quantity": 0,
    "total_buy_value": 0,
    "total_sell_value": 0,
    "buy_avg_price": 0,
    "sell_avg_price": 0,
}

config = configparser.ConfigParser()
if os.path.exists("oanda.cfg"):
    config.read("oanda.cfg")
    account_id = config["oanda"]["account_id"]
    access_token = config["oanda"]["access_token"]
    account_type = config["oanda"]["account_type"]
else:
    account_id = os.getenv("account_id")
    access_token = os.getenv("access_token")
    account_type = os.getenv("account_type")

client = oandapyV20.API(access_token=access_token)
                        
instrument = "EUR_USD"
params = {"instruments": instrument}
r = pricing.PricingInfo(accountID=account_id, params=params)
