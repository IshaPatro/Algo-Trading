import config

def update_metrics(order_type, price, quantity, strategy):
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
