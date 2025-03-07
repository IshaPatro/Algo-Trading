from queue import Queue
from threading import Lock
import pandas as pd
import configparser
import oandapyV20
import oandapyV20.endpoints.pricing as pricing

STRONG_SIGNAL_QUANTITY = 10000000
WEAK_SIGNAL_QUANTITY = 500000
SMA_50_WINDOW = 50
SMA_200_WINDOW = 200
RSI_WINDOW = 14

price_data = []
orders_history = []
orderbook_data = []
data_lock = Lock()

orders_queue = Queue()
metrics_queue = Queue()
orderbook_queue = Queue()

trading_metrics = {
    "total_pnl": 0,
}

config = configparser.ConfigParser()
config.read("oanda.cfg")
account_id = config["oanda"]["account_id"]
access_token = config["oanda"]["access_token"]
account_type = config["oanda"]["account_type"]
client = oandapyV20.API(access_token=access_token)
                        
instrument = "EUR_USD"
params = {"instruments": instrument}
r = pricing.PricingInfo(accountID=account_id, params=params)
