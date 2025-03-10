from threading import Event, Thread
from dataStream import stream_data
from dashboard import create_app as create_dashboard_app
import dash
import os

# Initialize data stream function
def initialize_data_stream():
    stop_event = Event()
    data_thread = Thread(target=stream_data, args=(stop_event,))
    data_thread.daemon = True
    data_thread.start()
    return stop_event

# Create the app instance at module level for Gunicorn to find
app = create_dashboard_app()

# Add server variable for Gunicorn
server = app.server

# Initialize data stream for both direct run and Gunicorn
stop_event = initialize_data_stream()

if __name__ == "__main__":
    # Get port from environment variable for Heroku compatibility
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=False, port=port, host="0.0.0.0")
    