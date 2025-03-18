import config
import datetime
from orderHistory import clear_order_history

last_order_count = 0

def update_metrics(order_type, price, quantity, strategy):
    global last_order_count
    
    metrics = config.trading_metrics.copy()
    
    if order_type == "BUY":
        metrics["total_buy_quantity"] += quantity
        metrics["total_buy_value"] += price * quantity
        if metrics["total_buy_quantity"] > 0:
            metrics["buy_avg_price"] = metrics["total_buy_value"] / metrics["total_buy_quantity"]
    elif order_type == "SELL":
        metrics["total_sell_quantity"] += quantity
        metrics["total_sell_value"] += price * quantity
        if metrics["total_sell_quantity"] > 0:
            metrics["sell_avg_price"] = metrics["total_sell_value"] / metrics["total_sell_quantity"]
    
    min_quantity = min(metrics["total_buy_quantity"], metrics["total_sell_quantity"])
    if min_quantity > 0 and metrics["buy_avg_price"] > 0 and metrics["sell_avg_price"] > 0:
        metrics["total_pnl"] = (metrics["sell_avg_price"] - metrics["buy_avg_price"]) * min_quantity
    
    config.metrics_queue.put(metrics)
    config.trading_metrics.update(metrics)
    
    current_order_count = len(config.orders_history)
    last_order_count = current_order_count

def initialize_metrics_from_history():
    config.trading_metrics = {
        "total_pnl": 0,
        "total_buy_quantity": 0,
        "total_sell_quantity": 0,
        "total_buy_value": 0,
        "total_sell_value": 0,
        "buy_avg_price": 0,
        "sell_avg_price": 0,
    }
    
    for order in config.orders_history:
        try:
            order_type = order.get("type")
            price = float(order.get("price", 0))
            quantity = float(order.get("quantity", 0))
            strategy = order.get("strategy", "unknown")
            
            if order_type == "BUY":
                config.trading_metrics["total_buy_quantity"] += quantity
                config.trading_metrics["total_buy_value"] += price * quantity
                if config.trading_metrics["total_buy_quantity"] > 0:
                    config.trading_metrics["buy_avg_price"] = config.trading_metrics["total_buy_value"] / config.trading_metrics["total_buy_quantity"]
            elif order_type == "SELL":
                config.trading_metrics["total_sell_quantity"] += quantity
                config.trading_metrics["total_sell_value"] += price * quantity
                if config.trading_metrics["total_sell_quantity"] > 0:
                    config.trading_metrics["sell_avg_price"] = config.trading_metrics["total_sell_value"] / config.trading_metrics["total_sell_quantity"]
        except Exception as e:
            print(f"Error processing order for metrics initialization: {e}")
    
    min_quantity = min(config.trading_metrics["total_buy_quantity"], config.trading_metrics["total_sell_quantity"])
    if min_quantity > 0 and config.trading_metrics["buy_avg_price"] > 0 and config.trading_metrics["sell_avg_price"] > 0:
        config.trading_metrics["total_pnl"] = (config.trading_metrics["sell_avg_price"] - config.trading_metrics["buy_avg_price"]) * min_quantity
    
    print(f"Metrics initialized from {len(config.orders_history)} historical orders")
    global last_order_count
    last_order_count = len(config.orders_history)

def reset_metrics():
    config.trading_metrics = {
        "total_pnl": 0,
        "total_buy_quantity": 0,
        "total_sell_quantity": 0,
        "total_buy_value": 0,
        "total_sell_value": 0,
        "buy_avg_price": 0,
        "sell_avg_price": 0,
    }
    global last_order_count
    last_order_count = 0
    clear_order_history()
    print(f"Trading metrics reset at {datetime.datetime.now()}")
