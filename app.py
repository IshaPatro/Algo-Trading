import time
from threading import Event, Thread
import config
from data_stream import stream_data
from dashboard import create_app

def main():
    # Print configuration information
    print(f"Starting trading application for {config.instrument}")
    print(f"Account ID: {config.account_id}")
    print(f"Account Type: {config.account_type}")
    
    # Initialize and start data streaming thread
    stop_event = Event()
    data_thread = Thread(target=stream_data, args=(stop_event,))
    data_thread.daemon = True
    data_thread.start()
    
    # Create and run dashboard
    app = create_app()
    app.run_server(debug=False, port=9000)

if __name__ == "__main__":
    try:
        # Clean up any existing threads if restarting
        stop_event = Event()
        stop_event.set()
        time.sleep(1)
    except:
        pass
    
    main()