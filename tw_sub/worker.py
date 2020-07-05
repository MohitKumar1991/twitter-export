import sys, time, os
import threading, logging
from .daemon import Daemon

logging.basicConfig(level=logging.DEBUG, format='%(threadName)s :: %(message)s')

class workerdaemon(Daemon):
    def run(self):
        self.stop_event = threading.Event()
        from .followers import FollowersTask
        from .campaign import CampaignsTask
        
        def start_followers_task(stop_event):
            ftasks = FollowersTask(stop_event=self.stop_event)
            ftasks.run()

        def start_campaign_task(stop_event):
            ctask = CampaignsTask(stop_event=self.stop_event)
            ctask.run()

        self.followers_thread = None
        self.campaign_thread = None
        
        self.followers_thread = threading.Thread(name="followers",target=start_followers_task, args=(self.stop_event,))
        self.campaign_thread = threading.Thread(name="campaigns", target=start_campaign_task, args=(self.stop_event,))
        self.followers_thread.start()
        self.campaign_thread.start()

    def quit(self):
        self.stop_event.set()
        self.followers_thread.join()
        self.campaign_thread.join()

daemon = workerdaemon()

if 'start' == sys.argv[1]: 
    daemon.start()
elif 'stop' == sys.argv[1]: 
    daemon.stop()
elif 'restart' == sys.argv[1]: 
    daemon.restart()



