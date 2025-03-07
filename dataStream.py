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
    
    print("SMA-50 Trading - Current price:", current_price, "SMA-50:", current_sma_50)
    
    current_price_above_sma_50 = current_price > current_sma_50
    
    if previous_price_above_sma_50 is not None:
        if not previous_price_above_sma_50 and current_price_above_sma_50:
            place_order("BUY", ask_price, config.WEAK_SIGNAL_QUANTITY, "Break Above SMA-50")
            print("BUY Signal: Price crossed above SMA-50")
        
        elif previous_price_above_sma_50 and not current_price_above_sma_50:
            place_order("SELL", bid_price, config.WEAK_SIGNAL_QUANTITY, "Break Below SMA-50")
            print("SELL Signal: Price crossed below SMA-50")
    
    return current_price_above_sma_50

def execute_trading_strategy(df, bid_price, ask_price, previous_price_above_sma_50):
    current_price = df["Mid"].iloc[-1]
    current_sma_50 = df["SMA_50"].iloc[-1]
    current_sma_200 = df["SMA_200"].iloc[-1] if "SMA_200" in df else None
    current_rsi = df["RSI"].iloc[-1] if "RSI" in df else 50
    
    print("Trading Strategy - Current values:", current_sma_50, current_sma_200, current_price)
    
    if len(df) < 200:
        current_price_above_sma_50 = current_price > current_sma_50
        
        if previous_price_above_sma_50 is not None:
            if not previous_price_above_sma_50 and current_price_above_sma_50:
                place_order("BUY", ask_price, config.WEAK_SIGNAL_QUANTITY, "Break Above SMA-50")
                print("BUY Signal: Price crossed above SMA-50 (Small Order)")
            
            elif previous_price_above_sma_50 and not current_price_above_sma_50:
                place_order("SELL", bid_price, config.WEAK_SIGNAL_QUANTITY, "Break Below SMA-50")
                print("SELL Signal: Price crossed below SMA-50 (Small Order)")
        
        return current_price_above_sma_50
    
    else:
        if len(df) > 1:
            prev_sma_50 = df["SMA_50"].iloc[-2]
            prev_sma_200 = df["SMA_200"].iloc[-2]
            prev_price = df["Mid"].iloc[-2]

            print("Trading Strategy - Previous values:", prev_sma_50, prev_sma_200, prev_price)
            
            if prev_sma_50 < prev_sma_200 and current_sma_50 > current_sma_200:
                if current_rsi > 50:
                    place_order("BUY", ask_price, config.STRONG_SIGNAL_QUANTITY, "Golden Cross")
                    print("BUY Signal: Golden Cross (Large Order)")
            
            elif prev_sma_50 > prev_sma_200 and current_sma_50 < current_sma_200:
                place_order("SELL", bid_price, config.STRONG_SIGNAL_QUANTITY, "Death Cross")
                print("SELL Signal: Death Cross (Large Order)")
            
            current_price_above_sma_50 = current_price > current_sma_50
            
            if previous_price_above_sma_50 is not None:
                if not previous_price_above_sma_50 and current_price_above_sma_50:
                    if current_rsi > 50:
                        place_order("BUY", ask_price, config.WEAK_SIGNAL_QUANTITY, "Break Above SMA-50")
                        print("BUY Signal: Price crossed above SMA-50 (Small Order)")
                
                elif previous_price_above_sma_50 and not current_price_above_sma_50:
                    if current_rsi < 50:
                        place_order("SELL", bid_price, config.WEAK_SIGNAL_QUANTITY, "Break Below SMA-50")
                        print("SELL Signal: Price crossed below SMA-50 (Small Order)")
            
            if prev_price < prev_sma_50 and current_price > current_sma_50 and current_price_above_sma_50:
                if abs(prev_price - prev_sma_50) / prev_sma_50 < 0.0005:
                    place_order("BUY", ask_price, config.WEAK_SIGNAL_QUANTITY, "SMA-50 Support")
                    print("BUY Signal: SMA-50 Support (Small Order)")
            
            if prev_price > prev_sma_50 and current_price < current_sma_50 and not current_price_above_sma_50:
                if abs(prev_price - prev_sma_50) / prev_sma_50 < 0.0005:
                    place_order("SELL", bid_price, config.WEAK_SIGNAL_QUANTITY, "SMA-50 Resistance")
                    print("SELL Signal: SMA-50 Resistance (Small Order)")
            
            return current_price_above_sma_50
        else:
            return current_price > current_sma_50

def stream_data(stop_event):
    previous_price_above_sma_50 = None
    params = {
        "instruments": config.instrument
    }
    r = pricing.PricingInfo(accountID=config.account_id, params=params)
    
    use_real_api = True
    print("Using real API for pricing")
    
    while not stop_event.is_set():
        try:
            if use_real_api:
                response = config.client.request(r)
                
                bids = response["prices"][0]["bids"]
                asks = response["prices"][0]["asks"]
            else:
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
           
            config.price_data.append(new_data)
            
            if len(config.price_data) >= config.SMA_200_WINDOW:
                df = pd.DataFrame(config.price_data[-config.SMA_200_WINDOW:])
                df["SMA_50"] = df["Mid"].rolling(window=config.SMA_50_WINDOW, min_periods=1).mean()
                df["SMA_200"] = df["Mid"].rolling(window=config.SMA_200_WINDOW, min_periods=1).mean()

                print("Length of df: ", len(df))
                if len(df) >= config.RSI_WINDOW:
                    df["RSI"] = calculate_rsi(df["Mid"], config.RSI_WINDOW)
                previous_price_above_sma_50 = execute_trading_strategy(df, bid_price, ask_price, previous_price_above_sma_50)
            else:
                min_required = min(len(config.price_data), config.SMA_50_WINDOW)
                if min_required > 0:
                    df = pd.DataFrame(config.price_data[-min_required:])
                    df["SMA_50"] = df["Mid"].rolling(window=min_required, min_periods=1).mean()
                    
                    print("Short data length of df: ", len(df))
                    previous_price_above_sma_50 = execute_sma50_trading(df, bid_price, ask_price, previous_price_above_sma_50)
        except Exception as e:
            print(f"Error in stream_data: {e}")
        
        time.sleep(1)