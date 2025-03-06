import datetime
import time
import pandas as pd
from orderManager import place_order
from indicators import calculate_rsi
import config
import oandapyV20.endpoints.orders as orders


def stream_data(stop_event):
    previous_price_above_sma_50 = None
    
    # For testing without actual connection, generate sample data
    try:
        from oanda import pricing
        # Create the pricing request for the instrument
        params = {
            "instruments": config.instrument
        }
        r = pricing.PricingInfo(accountID=config.account_id, params=params)
        
        use_real_api = True
        print("Using real API for pricing")
    except Exception as e:
        print(f"Could not initialize API pricing: {e}")
        print("Using simulated price data")
        use_real_api = False
    
    while not stop_event.is_set():
        try:
            if use_real_api:
                # Get pricing from the API
                response = config.client.request(r)
                
                bids = response["prices"][0]["bids"]
                asks = response["prices"][0]["asks"]
            else:
                # Create simulated data for testing
                import random
                base_price = 1.1000 + (random.random() - 0.5) * 0.01
                
                bids = [
                    {"price": str(base_price - 0.0001 * i), "liquidity": str(random.randint(100000, 1000000))}
                    for i in range(5)
                ]
                
                asks = [
                    {"price": str(base_price + 0.0001 * (i + 1)), "liquidity": str(random.randint(100000, 1000000))}
                    for i in range(5)
                ]
                
                # Simulate API response
                response = {
                    "prices": [{
                        "bids": bids,
                        "asks": asks
                    }]
                }
            
            top_bids = bids[:5] if len(bids) >= 5 else bids
            top_asks = asks[:5] if len(asks) >= 5 else asks
            
            orderbook = {
                "timestamp": datetime.datetime.now(),
                "bids": top_bids,
                "asks": top_asks
            }
            
            # Put orderbook data in the queue for display
            config.orderbook_queue.put(orderbook)
            
            bid_price = float(response["prices"][0]["bids"][0]["price"])
            ask_price = float(response["prices"][0]["asks"][0]["price"])
            mid_price = (bid_price + ask_price) / 2
            timestamp = datetime.datetime.now()
            
            new_data = {
                "Timestamp": timestamp, 
                "Bid": bid_price, 
                "Ask": ask_price,
                "Mid": mid_price
            }
            
            with config.data_lock:
                config.price_data.append(new_data)
                
                if len(config.price_data) >= config.SMA_200_WINDOW:
                    df = pd.DataFrame(config.price_data[-config.SMA_200_WINDOW:])
                    df["SMA_50"] = df["Mid"].rolling(window=config.SMA_50_WINDOW, min_periods=1).mean()
                    df["SMA_200"] = df["Mid"].rolling(window=config.SMA_200_WINDOW, min_periods=1).mean()

                    print("Length of df: ", len(df))
                    if len(df) >= config.RSI_WINDOW:
                        df["RSI"] = calculate_rsi(df["Mid"], config.RSI_WINDOW)
                    
                    current_price = df["Mid"].iloc[-1]
                    current_sma_50 = df["SMA_50"].iloc[-1]
                    current_sma_200 = df["SMA_200"].iloc[-1]
                    current_rsi = df["RSI"].iloc[-1] if "RSI" in df else 50
                    
                    if len(df) > 1:
                        prev_sma_50 = df["SMA_50"].iloc[-2]
                        prev_sma_200 = df["SMA_200"].iloc[-2]
                        prev_price = df["Mid"].iloc[-2]

                        print(prev_sma_50, prev_sma_200, prev_price)
                        
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
                        
                        previous_price_above_sma_50 = current_price_above_sma_50
                    else:
                        previous_price_above_sma_50 = current_price > current_sma_50
                    
        except Exception as e:
            print(f"Error in stream_data: {e}")
        
        time.sleep(1)