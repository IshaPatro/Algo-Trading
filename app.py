from threading import Event, Thread
from dataStream import stream_data
from dashboard import create_app as create_dashboard_app
import dash
import os

# Create the app instance at module level for Gunicorn to find
app = create_dashboard_app()

# Add server variable for Gunicorn
server = app.server

# Initialize data stream only when running the app directly
def initialize_data_stream():
    stop_event = Event()
    data_thread = Thread(target=stream_data, args=(stop_event,))
    data_thread.daemon = True
    data_thread.start()
    return stop_event

if __name__ == "__main__":
    stop_event = initialize_data_stream()
    # Get port from environment variable for Heroku compatibility
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=False, port=port, host="0.0.0.0")
    