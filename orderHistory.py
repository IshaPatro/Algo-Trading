import json
import os
import datetime


ORDER_HISTORY_FILE = 'order_history.json'

def save_orders(orders):
    try:
        with open(ORDER_HISTORY_FILE, 'w') as f:
            json.dump(orders, f)
    except Exception as e:
        print(f"Error saving orders to file: {e}")

def load_orders():
    if not os.path.exists(ORDER_HISTORY_FILE):
        return []
    
    try:
        with open(ORDER_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading orders from file: {e}")
        return []

def clear_order_history():
    try:
        if os.path.exists(ORDER_HISTORY_FILE):
            with open(ORDER_HISTORY_FILE, 'w') as f:
                json.dump([], f)
            print(f"Order history file cleared at {datetime.datetime.now()}")
    except Exception as e:
        print(f"Error clearing order history file: {e}")