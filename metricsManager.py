import config

def update_metrics(pnl, strategy):
    with config.data_lock:
        metrics = config.trading_metrics.copy()
        metrics["total_pnl"] += pnl
        config.metrics_queue.put(metrics)
        config.trading_metrics.update(metrics)
