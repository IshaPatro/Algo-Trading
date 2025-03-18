from threading import Event, Thread
from dataStream import stream_data
from dashboard import create_app as create_dashboard_app
import dash
import os
from scheduler import initialize_scheduler

def initialize_data_stream():
    stop_event = Event()
    data_thread = Thread(target=stream_data, args=(stop_event,))
    data_thread.daemon = True
    data_thread.start()
    return stop_event

app = create_dashboard_app()

server = app.server

stop_event = initialize_data_stream()
scheduler = initialize_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=False, port=port, host="0.0.0.0")
    