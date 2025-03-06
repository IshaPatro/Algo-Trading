import datetime
import config
from metricsManager import update_metrics
import oandapyV20.endpoints.orders as orders

def place_order(order_type, price, quantity, strategy):
    try:
        print("Placing order...")
        units = str(quantity) if order_type == "BUY" else str(-quantity)
        
        order_data = {
            "order": {
                "units": units,
                "instrument": config.instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT",
            }
        }

        order_request = orders.OrderCreate(accountID=config.account_id, data=order_data)
        response = config.client.request(order_request)
        
        order_id = response["orderCreateTransaction"]["id"]
        execution_price = float(response["orderCreateTransaction"]["price"])
        
        order_time = datetime.datetime.now()
        
        order_record = {
            "order_id": order_id,
            "type": order_type,
            "quantity": quantity,
            "price": execution_price,
            "timestamp": order_time.isoformat(),
            "instrument": config.instrument,
            "strategy": strategy
        }
        
        config.orders_queue.put(order_record)
        print(f"Order added to queue: {order_record}")
        
        if order_type == "BUY":
            pnl = (price - execution_price) * quantity
        else:
            pnl = (execution_price - price) * quantity
        
        update_metrics(pnl, strategy)
        
    except Exception as e:
        print(f"Error in place_order: {e}")