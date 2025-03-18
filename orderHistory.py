import json
import os
import datetime

ORDER_HISTORY_FILE = 'order_history.json'

# In-memory storage for Heroku environment
in_memory_orders = []

# Check if running on Heroku
is_heroku = os.environ.get("DYNO") is not None

def save_orders(orders):
    global in_memory_orders
    
    # Update in-memory storage regardless of environment
    in_memory_orders = orders
    
    # Only write to file if not on Heroku
    if not is_heroku:
        try:
            with open(ORDER_HISTORY_FILE, 'w') as f:
                json.dump(orders, f)
        except Exception as e:
            print(f"Error saving orders to file: {e}")

def load_orders():
    global in_memory_orders
    
    # If on Heroku, use in-memory storage
    if is_heroku:
        return in_memory_orders
    
    # Otherwise, try to load from file
    if not os.path.exists(ORDER_HISTORY_FILE):
        return []
    
    try:
        with open(ORDER_HISTORY_FILE, 'r') as f:
            loaded_orders = json.load(f)
            in_memory_orders = loaded_orders  # Update in-memory storage
            return loaded_orders
    except Exception as e:
        print(f"Error loading orders from file: {e}")
        return []

def clear_order_history():
    global in_memory_orders
    
    # Clear in-memory storage
    in_memory_orders = []
    
    # Only clear file if not on Heroku
    if not is_heroku:
        try:
            if os.path.exists(ORDER_HISTORY_FILE):
                with open(ORDER_HISTORY_FILE, 'w') as f:
                    json.dump([], f)
                print(f"Order history file cleared at {datetime.datetime.now()}")
        except Exception as e:
            print(f"Error clearing order history file: {e}")
    else:
        print(f"In-memory order history cleared at {datetime.datetime.now()}")