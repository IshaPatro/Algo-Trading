import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import config
from threading import Event

reset_event = Event()

def reset_application_data():
    """
    Reset all application data at midnight EST
    This function clears all stored data and resets metrics
    """
    print(f"Resetting application data at {datetime.datetime.now(pytz.timezone('US/Eastern'))}")

    with config.data_lock:
        config.price_data.clear()
        config.orders_history.clear()
        config.orderbook_data.clear()
        
        config.trading_metrics = {
            "total_pnl": 0,
            "total_buy_quantity": 0,
            "total_sell_quantity": 0,
            "total_buy_value": 0,
            "total_sell_value": 0,
            "buy_avg_price": 0,
            "sell_avg_price": 0,
        }
    
    reset_event.set()
    print("Application data has been reset successfully")

def initialize_scheduler():
    """
    Initialize the scheduler to reset the application at midnight EST
    """
    scheduler = BackgroundScheduler()
    
    scheduler.add_job(
        reset_application_data,
        CronTrigger(hour=0, minute=0, second=0, timezone=pytz.timezone('US/Eastern')),
        id='reset_job',
        replace_existing=True
    )
    
    scheduler.start()
    print("Scheduler initialized - Application will reset daily at 12am EST")
    
    return scheduler