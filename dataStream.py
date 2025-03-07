import datetime
import time
import pandas as pd
from orderManager import place_order
from indicators import calculate_rsi
import config
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.pricing as pricing

def execute_sma50_trading(df, bid_price, ask_price, previous_price_above_sma_50):
    current_price = df["Mid"].iloc[-1]
    current_sma_50 = df["SMA_50"].iloc[-1]
    
    current_price_above_sma_50 = current_price > current_sma_50
    
    if previous_price_above_sma_50 is not None:
        if not previous_price_above_sma_50 and current_price_above_sma_50:
            place_order("BUY", ask_price, config.WEAK_SIGNAL_QUANTITY, "Break Above SMA-50")
        
        elif previous_price_above_sma_50 and not current_price_above_sma_50:
            place_order("SELL", bid_price, config.WEAK_SIGNAL_QUANTITY, "Break Below SMA-50")
    
    return current_price_above_sma_50

def execute_trading_strategy(df, bid_price, ask_price, previous_price_above_sma_50):
    current_price = df["Mid"].iloc[-1]
    current_sma_50 = df["SMA_50"].iloc[-1]
    current_sma_200 = df["SMA_200"].iloc[-1] if "SMA_200" in df else None
    current_rsi = df["RSI"].iloc[-1] if "RSI" in df else 50
    
    if len(df) < 200:
        current_price_above_sma_50 = current_price > current_sma_50
        
        if previous_price_above_sma_50 is not None:
            if not previous_price_above_sma_50 and current_price_above_sma_50:
                place_order("BUY", ask_price, config.WEAK_SIGNAL_QUANTITY, "Break Above SMA-50")
            
            elif previous_price_above_sma_50 and not current_price_above_sma_50:
                place_order("SELL", bid_price, config.WEAK_SIGNAL_QUANTITY, "Break Below SMA-50")
        
        return current_price_above_sma_50
    
    else:
        if len(df) > 1:
            prev_sma_50 = df["SMA_50"].iloc[-2]
            prev_sma_200 = df["SMA_200"].iloc[-2]
            prev_price = df["Mid"].iloc[-2]
            
            if prev_sma_50 < prev_sma_200 and current_sma_50 > current_sma_200:
                if current_rsi > 50:
                    place_order("BUY", ask_price, config.STRONG_SIGNAL_QUANTITY, "Golden Cross")
            
            elif prev_sma_50 > prev_sma_200 and current_sma_50 < current_sma_200:
                place_order("SELL", bid_price, config.STRONG_SIGNAL_QUANTITY, "Death Cross")
            
            current_price_above_sma_50 = current_price > current_sma_50
            
            if previous_price_above_sma_50 is not None:
                if not previous_price_above_sma_50 and current_price_above_sma_50:
                    if current_rsi > 50:
                        place_order("BUY", ask_price, config.WEAK_SIGNAL_QUANTITY, "Break Above SMA-50")
                
                elif previous_price_above_sma_50 and not current_price_above_sma_50:
                    if current_rsi < 50:
                        place_order("SELL", bid_price, config.WEAK_SIGNAL_QUANTITY, "Break Below SMA-50")
            
            if prev_price < prev_sma_50 and current_price > current_sma_50 and current_price_above_sma_50:
                if abs(prev_price - prev_sma_50) / prev_sma_50 < 0.0005:
                    place_order("BUY", ask_price, config.WEAK_SIGNAL_QUANTITY, "SMA-50 Support")
            
            if prev_price > prev_sma_50 and current_price < current_sma_50 and not current_price_above_sma_50:
                if abs(prev_price - prev_sma_50) / prev_sma_50 < 0.0005:
                    place_order("SELL", bid_price, config.WEAK_SIGNAL_QUANTITY, "SMA-50 Resistance")
            
            return current_price_above_sma_50
        else:
            return current_price > current_sma_50

def stream_data(stop_event):
    previous_price_above_sma_50 = None
    params = {
        "instruments": config.instrument
    }
    r = pricing.PricingInfo(accountID=config.account_id, params=params)
    
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
                        
                        previous_price_above_sma_50 = execute_trading_strategy(df, bid, ask, previous_price_above_sma_50)
                    
                    orderbook = {
                        "bids": price["bids"],
                        "asks": price["asks"],
                        "timestamp": timestamp
                    }
                    config.orderbook_queue.put(orderbook)
            
        except Exception as e:
            pass
        
        time.sleep(1)