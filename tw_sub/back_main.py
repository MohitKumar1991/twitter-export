#this is a background process which will create the indexes etc
import threading
from .followers import FollowersTask
from .campaign import CampaignsTask
from .config import USERNAME
import time, sys
import signal
from flask import Flask

app = Flask("Indexer")
stop_event = threading.Event()



def start_followers_task(stop_event):
    ftasks = FollowersTask(username=USERNAME, stop_event=stop_event)
    ftasks.run()

def start_campaign_task(stop_event):
    ctask = CampaignsTask(stop_event=stop_event)
    ctask.run()


# followers_thread = threading.Thread(target=start_followers_task, args=(stop_event,))
campaign_thread = threading.Thread(target=start_campaign_task, args=(stop_event,))

@app.route('/status', methods=['GET'])
def status():
    if campaign_thread.curr_campaign is not None:
        status = 'Running {0}  ::  {1}'.format(campaign_thread.curr_campaign['id'], campaign_thread.curr_campaign['name'])
    else:
        status = 'Idle'
    return { 'runner_status': True, 'followers_status':  True, 'campaigns_status': status }


def shutdown(sig, stackframe):
    print('GOT INTO SHUTDOWN')
    stop_event.set()
    # followers_thread.join()
    campaign_thread.join()
    sys.exit(0)

def runner():
    # followers_thread.start()
    # campaign_thread.start()
    campaign_thread.run()
    signal.signal(signal.SIGINT, shutdown)
    app.run(debug=True)