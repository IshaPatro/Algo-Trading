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
    
    # Enhanced error handling variables
    retry_count = 0
    max_retries = 10
    retry_delay = 2
    backoff_factor = 1.5
    max_backoff = 30
    
    # Set a longer timeout for production environments
    config.client.request_timeout = 120
    
    # Initialize with a default data point to prevent "waiting for data" message
    timestamp = datetime.datetime.now()
    default_bid = 1.0800
    default_ask = 1.0802
    default_mid = (default_bid + default_ask) / 2
    
    with config.data_lock:
        config.price_data.append({
            "Timestamp": timestamp,
            "Bid": default_bid,
            "Ask": default_ask,
            "Mid": default_mid
        })
        
        # Add initial orderbook data
        initial_orderbook = {
            "bids": [{"price": str(default_bid), "liquidity": "10000"}],
            "asks": [{"price": str(default_ask), "liquidity": "10000"}],
            "timestamp": timestamp
        }
        config.orderbook_queue.put(initial_orderbook)
    
    print("Added default data point to initialize the dashboard")
    
    while not stop_event.is_set():
        try:
            response = config.client.request(r)
            prices = response["prices"]
            
            if not prices:
                print("Received empty prices array, retrying...")
                time.sleep(retry_delay)
                continue
            
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
            
            # Reset retry count on successful request
            retry_count = 0
            retry_delay = 2  # Reset delay on success
            
        except Exception as e:
            retry_count += 1
            current_delay = min(retry_delay * (backoff_factor ** (retry_count - 1)), max_backoff)
            print(f"Error in data stream: {e} (Attempt {retry_count}, waiting {current_delay}s)")
            
            if retry_count >= max_retries:
                print("Maximum retry attempts reached, resetting and continuing...")
                # Add a placeholder data point with current timestamp to keep dashboard updating
                placeholder_timestamp = datetime.datetime.now()
                
                with config.data_lock:
                    if config.price_data and len(config.price_data) > 0:
                        last_bid = config.price_data[-1]["Bid"]
                        last_ask = config.price_data[-1]["Ask"]
                        last_mid = config.price_data[-1]["Mid"]
                    else:
                        last_bid = 1.0800
                        last_ask = 1.0802
                        last_mid = (last_bid + last_ask) / 2
                    
                    config.price_data.append({
                        "Timestamp": placeholder_timestamp,
                        "Bid": last_bid,
                        "Ask": last_ask,
                        "Mid": last_mid
                    })
                    
                    # Add placeholder orderbook data
                    placeholder_orderbook = {
                        "bids": [{"price": str(last_bid), "liquidity": "10000"}],
                        "asks": [{"price": str(last_ask), "liquidity": "10000"}],
                        "timestamp": placeholder_timestamp
                    }
                    config.orderbook_queue.put(placeholder_orderbook)
                
                print(f"Added placeholder data point to maintain dashboard updates")
                retry_count = 0
                retry_delay = 2  # Reset delay
            
            time.sleep(current_delay)
            continue
        
        time.sleep(1)