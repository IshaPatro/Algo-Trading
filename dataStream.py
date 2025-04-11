import datetime
import time
import pandas as pd
from orderManager import place_order
from indicators import calculate_rsi
import config
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.pricing as pricing
from metricsManager import reset_metrics

def execute_trading_strategy(df, bid_price, ask_price, previous_price_above_sma_50):
    current_price = df["Mid"].iloc[-1]
    current_sma_50 = df["SMA_50"].iloc[-1]
    current_sma_200 = df["SMA_200"].iloc[-1] if "SMA_200" in df else None
    current_rsi = df["RSI"].iloc[-1] if "RSI" in df else 50
    
    if config.trading_metrics["buy_avg_price"] > 0 and config.trading_metrics["total_buy_quantity"] > config.trading_metrics["total_sell_quantity"]:
        profit_threshold = config.trading_metrics["buy_avg_price"] + config.PROFIT_THRESHOLD_PIPS
        loss_threshold = config.trading_metrics["buy_avg_price"] - config.LOSS_THRESHOLD_PIPS
        remaining_quantity = config.trading_metrics["total_buy_quantity"] - config.trading_metrics["total_sell_quantity"]
        
        if current_price >= profit_threshold and remaining_quantity > 0:
            place_order("SELL", bid_price, config.PROFIT_BOOKING_QUANTITY, "Profit Booking")
            reset_metrics()
            return previous_price_above_sma_50
        
        elif current_price <= loss_threshold and remaining_quantity > 0:
            place_order("SELL", bid_price, config.PROFIT_BOOKING_QUANTITY, "Stop Loss")
            reset_metrics()
            return previous_price_above_sma_50
    
    if len(df) > 1:
        prev_sma_50 = df["SMA_50"].iloc[-2]
        prev_sma_200 = df["SMA_200"].iloc[-2] if "SMA_200" in df else None
        prev_price = df["Mid"].iloc[-2]
        
        if "SMA_200" in df and prev_sma_200 is not None and current_sma_200 is not None:
            if prev_sma_50 < prev_sma_200 and current_sma_50 > current_sma_200:
                place_order("BUY", ask_price, config.STRONG_SIGNAL_QUANTITY, "Golden Cross")
            
            elif prev_sma_50 > prev_sma_200 and current_sma_50 < current_sma_200:
                place_order("SELL", bid_price, config.STRONG_SIGNAL_QUANTITY, "Death Cross")
        
        current_price_above_sma_50 = current_price > current_sma_50
        
        return current_price_above_sma_50
    else:
        return current_price > current_sma_50

def stream_data(stop_event):
    previous_price_above_sma_50 = None
    params = {
        "instruments": config.instrument
    }
    r = pricing.PricingInfo(accountID=config.account_id, params=params)
    print(f"Starting data stream for {config.instrument} on account {config.account_id}")
    # Set a longer timeout for production environments
    config.client.request_timeout = 60
    
    while not stop_event.is_set():
        try:
            response = config.client.request(r)
            prices = response["prices"]
            
            for price in prices:
                timestamp = datetime.datetime.strptime(price["time"].split(".")[0], "%Y-%m-%dT%H:%M:%S")
                bid = float(price["bids"][0]["price"])
                ask = float(price["asks"][0]["price"])
                mid = (bid + ask) / 2
                
                with config.data_lock:
                    config.price_data.append({
                        "Timestamp": timestamp,
                        "Bid": bid,
                        "Ask": ask,
                        "Mid": mid
                    })
                    
                    if len(config.price_data) > 1000:
                        config.price_data = config.price_data[-1000:]
                    
                    df = pd.DataFrame(config.price_data)
                    
                    if len(df) > 1:
                        df["SMA_50"] = df["Mid"].rolling(window=config.SMA_50_WINDOW, min_periods=1).mean()
                        
                        if len(df) >= config.SMA_200_WINDOW:
                            df["SMA_200"] = df["Mid"].rolling(window=config.SMA_200_WINDOW, min_periods=1).mean()
                        
                        df["RSI"] = calculate_rsi(df["Mid"], window=config.RSI_WINDOW)
                        
                        try:
                            previous_price_above_sma_50 = execute_trading_strategy(df, bid, ask, previous_price_above_sma_50)
                            print(f"Trading strategy executed - Current price: {mid}, SMA_50: {df['SMA_50'].iloc[-1]}, Above SMA_50: {previous_price_above_sma_50}")
                        except Exception as strategy_error:
                            print(f"Error executing trading strategy: {strategy_error}")
                    
                    orderbook = {
                        "bids": price["bids"],
                        "asks": price["asks"],
                        "timestamp": timestamp
                    }
                    config.orderbook_queue.put(orderbook)
            
        except Exception as e:
            print(f"Error in data stream: {e}")
        
        time.sleep(1)