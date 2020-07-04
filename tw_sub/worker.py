import time, sys
import signal
import threading
from .followers import FollowersTask
from .campaign import CampaignsTask
def start_followers_task(stop_event):
    ftasks = FollowersTask(stop_event=stop_event)
    ftasks.run()

def start_campaign_task(stop_event):
    ctask = CampaignsTask(stop_event=stop_event)
    ctask.run()

def sigterm(sig, frame): 
    print("==== SIGTERM CALLED - SHUTTING DOWN ====", sig)
    stop_event.set()
    followers_thread.join()
    campaign_thread.join()
signal.signal(signal.SIGTERM, sigterm)
followers_thread = None
campaign_thread = None
stop_event = threading.Event()
followers_thread = threading.Thread(target=start_followers_task, args=(stop_event,))
campaign_thread = threading.Thread(target=start_campaign_task, args=(stop_event,))
followers_thread.start()
campaign_thread.start()