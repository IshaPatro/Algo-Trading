import datetime
import config
from metricsManager import update_metrics
import oandapyV20.endpoints.orders as orders
    
def place_order(order_type, price, quantity, strategy):
    try:
        print(f"Attempting to place {order_type} order at {price} for {quantity} units")
        print("Placing order...")
        units = str(quantity) if order_type == "BUY" else str(-quantity)
        
        # Create order data with proper structure for OANDA API
        order_data = {
            "order": {
                "units": units,
                "instrument": config.instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }

        # Add detailed logging to track the order process
        print(f"Sending order: {order_data}")
        print(f"Account ID being used: {config.account_id}")
        print(f"Instrument being traded: {config.instrument}")
        
        try:
            print(f"Creating order request object with account ID: {config.account_id}")
            order_request = orders.OrderCreate(accountID=config.account_id, data=order_data)
            print(f"Order request created: {order_request}")
            print(f"Sending request to API...")
            response = config.client.request(order_request)
            print(f"Order response received: {response}")
            
            if "orderCreateTransaction" not in response:
                print(f"WARNING: 'orderCreateTransaction' not found in response. Full response: {response}")
                return False
                
            order_id = response["orderCreateTransaction"]["id"]
            print(f"Order ID received: {order_id}")
            
            # For MARKET orders, the execution price might be in different places in the response
            execution_price = price  # Use the price parameter as fallback
            
            # Try to get the actual execution price if available in the response
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
            print(f"Order successfully executed and added to queue: {order_record}")
            
            if order_type == "BUY":
                pnl = (execution_price - price) * quantity
            else:
                pnl = (price - execution_price) * quantity
            
            update_metrics(pnl, strategy)
            return True
            
        except Exception as api_error:
            print(f"API Error in place_order: {api_error}")
            print(f"Error details: {str(api_error)}")
            return False
        
    except Exception as e:
        print(f"General Error in place_order: {e}")
        return False