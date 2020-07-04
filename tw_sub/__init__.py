__version__ = '0.1.0'   

# def start_worker():
#     import threading
#     stop_event = threading.Event()
#     from .campaign import CampaignsTask
#     ctask = CampaignsTask(stop_event=stop_event)
#     ctask.run()

def start_app():
    from flask import Flask
    import waitress
    from .main import app
    waitress.serve(app, host='127.0.0.1', port=8080)
    



