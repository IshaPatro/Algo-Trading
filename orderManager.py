import datetime
import config
from metricsManager import update_metrics
import oandapyV20.endpoints.orders as orders

def place_order(order_type, price, quantity, strategy):
    try:
        units = str(quantity) if order_type == "BUY" else str(-quantity)
        order_data = {
            "order": {
                "units": units,
                "instrument": config.instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        
        try:
            order_request = orders.OrderCreate(accountID=config.account_id, data=order_data)
            response = config.client.request(order_request)
            
            if "orderCreateTransaction" not in response:
                return False
            
            order_id = response["orderCreateTransaction"]["id"]
            execution_price = price
            
            if "orderFillTransaction" in response and "price" in response["orderFillTransaction"]:
                execution_price = float(response["orderFillTransaction"]["price"])
            elif "price" in response["orderCreateTransaction"]:
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
            
            pnl = (execution_price - price) * quantity if order_type == "BUY" else (price - execution_price) * quantity
            update_metrics(pnl, strategy)
            return True
            
        except Exception as api_error:
            return False
        
    except Exception:
        return False
