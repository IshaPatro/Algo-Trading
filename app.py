from threading import Event, Thread
from dataStream import stream_data
from dashboard import create_app as create_dashboard_app
import dash
import os
import time
from scheduler import initialize_scheduler

def initialize_data_stream():
    stop_event = Event()
    data_thread = Thread(target=stream_data, args=(stop_event,))
    data_thread.daemon = True
    data_thread.start()
    print("Data streaming thread started successfully")
    
    # Wait briefly to ensure thread initialization
    time.sleep(3)
    
    # Verify thread is running properly
    if data_thread.is_alive():
        print("Data thread verified as running")
    else:
        print("WARNING: Data thread may not have started properly")
        
    return stop_event, data_thread

app = create_dashboard_app()

server = app.server

# Initialize data stream with retry mechanism for production environments
max_retries = 3
retry_count = 0
while retry_count < max_retries:
    try:
        stop_event, data_thread = initialize_data_stream()
        # Check if thread is alive
        time.sleep(2)
        if data_thread.is_alive():
            print("Data stream initialized successfully")
            break
        else:
            print("Data thread failed to start, retrying...")
            retry_count += 1
    except Exception as e:
        print(f"Error initializing data stream: {e}")
        retry_count += 1
        time.sleep(2)

scheduler = initialize_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=False, port=port, host="0.0.0.0")
    