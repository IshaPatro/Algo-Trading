from threading import Event, Thread
from dataStream import stream_data
from dashboard import create_app as create_dashboard_app
import dash

app = create_dashboard_app()

if __name__ == "__main__":  
    stop_event = Event()
    data_thread = Thread(target=stream_data, args=(stop_event,))
    data_thread.daemon = True
    data_thread.start()
    app.run_server(debug=False, port=8050)
    