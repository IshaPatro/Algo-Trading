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
            print(f"Attempting to place {order_type} order for {quantity} units at {price} - Strategy: {strategy}")
            order_request = orders.OrderCreate(accountID=config.account_id, data=order_data)
            response = config.client.request(order_request)
            
            if "orderCreateTransaction" not in response:
                print(f"Order creation failed: 'orderCreateTransaction' not in response. Response: {response}")
                return False
            
            order_id = response["orderCreateTransaction"]["id"]
            execution_price = price
            
            if "orderFillTransaction" in response and "price" in response["orderFillTransaction"]:
                execution_price = float(response["orderFillTransaction"]["price"])
                print(f"Order filled at price: {execution_price}")
            elif "price" in response["orderCreateTransaction"]:
                execution_price = float(response["orderCreateTransaction"]["price"])
                print(f"Order created at price: {execution_price}")
            
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
            print(f"Order successfully placed and added to queue: {order_record}")
            
            update_metrics(order_type, execution_price, quantity, strategy)
            return True
            
        except Exception as api_error:
            print(f"API error when placing order: {api_error}")
            return False
        
    except Exception as e:
        print(f"Unexpected error when placing order: {e}")
        return False
