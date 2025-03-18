from threading import Event, Thread
from dataStream import stream_data
from dashboard import create_app as create_dashboard_app
import dash
import os
import sys
from scheduler import initialize_scheduler
import config
import traceback

def initialize_data_stream():
    try:
        stop_event = Event()
        data_thread = Thread(target=stream_data, args=(stop_event,))
        data_thread.daemon = True
        data_thread.start()
        return stop_event
    except Exception as e:
        print(f"Error initializing data stream: {e}")
        traceback.print_exc()
        return Event()

# Check if running on Heroku
is_heroku = os.environ.get("DYNO") is not None
if is_heroku:
    print("Running on Heroku environment")

# Check if OANDA credentials are available
if not config.access_token or not config.account_id:
    print("ERROR: OANDA API credentials are missing. Please set environment variables or create oanda.cfg file.")
    print("Required variables: account_id, access_token, account_type")
    # Don't exit in production as Heroku will restart the app
    if not is_heroku:  # Not running on Heroku
        sys.exit(1)

try:
    app = create_dashboard_app()
    server = app.server
    
    stop_event = initialize_data_stream()
    scheduler = initialize_scheduler()
    
    print("Application initialized successfully")
except Exception as e:
    print(f"ERROR initializing application: {e}")
    # Create a minimal app if the main app fails to initialize
    app = dash.Dash(__name__)
    app.layout = dash.html.Div([
        dash.html.H1("TradePulse - Error"),
        dash.html.P("There was an error initializing the application. Please check the logs.")
    ])
    server = app.server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=False, port=port, host="0.0.0.0")
    