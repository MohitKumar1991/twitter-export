from datetime import datetime, timedelta
from tweepy import RateLimitError, TweepError 
from .errors import AuthFailureError
import sqlite3, threading
import time, json, tweepy
from jinja2 import Template
from .utils import make_batches, load_state_worker
from .config import tweepyapi, CAMPAIGN_DB, campaign_db_worker, IS_AUTH, STATE_DB
from .campdb import get_one_follower, update_follower_id, get_pending_campaigns, change_campaign_status, get_current_campaign, get_all_followers


class CampaignsTask:
    def __init__(self, stop_event:threading.Event):
        self.stop_event = stop_event
        self.rate_limited = False
        self.auth = IS_AUTH
        self.curr_campaign = None
        self.tweepyapi = tweepyapi
        self.curr_followers = None
        state = load_state_worker(campaign_db_worker)
        self.last_run = datetime.strptime(state.get('last_run', '2010-06-16 23:57:08.027042'), '%Y-%m-%d %H:%M:%S.%f')
        #if there is no campaign active then turn one into active
        # self.tweepyapi = None # get from somewhere
        # self.curr_iterator = None
        #api.send_direct_message("1273873629969776641", "Hey! Nice to see you.")

    def stop(self):
        self.stop_event.set()

    def run(self):
        while not self.stop_event.is_set():
            self._ensure_current_active_campaign() #this will keep refreshign followers
            self._wait_till_available()
            try:
                self.do_task()
                self.rate_limited = False
            except RateLimitError as rle:
                print("RateLimitError", rle)
                self.rate_limited = True
            except AuthFailureError as afe:
                self.auth = False
                state_db = sqlite3.connect(STATE_DB)
                curr_state_db = store_state(state_db, {
                    'USER_KEY': '',
                    'USER_SECRET': ''
                })
                state_db.close()
            self._create_checkpoint()

    def _send_message(self, campaign_follower):
        #use jinja2 templating here
        t = Template(self.curr_campaign['message_template'])
        follower = get_one_follower(campaign_follower['follower_id'])
        if follower is None:
            print('FOllowers with ID {} not found'.format(campaign_follower['follower_id']))
            return
        msg = t.render(follower=follower)
        print("SENDING MESSAGE", msg, follower['id'])
        time.sleep(3)
        # self.tweepyapi.send_direct_message(str(follower['id']), msg)
        

    def _ensure_current_active_campaign(self):
        if self.curr_campaign is None:
            current_campaign = get_current_campaign()
            pending_campaigns = get_pending_campaigns()
            if current_campaign is None and len(pending_campaigns)> 0:
                change_campaign_status(pending_campaigns[0]['id'],'active')
                current_campaign = get_current_campaign()
            self.curr_campaign = current_campaign

        if self.curr_campaign is not None:  
            self.curr_followers = get_all_followers(self.curr_campaign['id'])
        print("_ensure_current_active_campaign", self.curr_campaign, self.curr_followers)

    # wait for IS_AUTH, AN ACTIVE CAMPAIGN, RATE_LIMIT AND INTERNET
    def _wait_till_available(self):
        while True:
            #keep trying for this
            if self.curr_campaign is None:
                self._ensure_current_active_campaign()
            if not self.auth or self.curr_campaign is None or (self.rate_limited and (datetime.now() - self.last_run) < timedelta(hours=1)):
                time.sleep(5)
            else:
                return

    
    #if all followers are done then set the status of the campaign as true
    def _create_checkpoint(self):
        pending = [ f for f in self.curr_followers if str(f['status']) == 'pending']
        if len(pending) == 0:
            change_campaign_status(self.curr_campaign['id'],'done')
            self.curr_campaign = None
            self.curr_followers = None
    
    def _mark_as_done(self, campaign_id, follower_id):
        update_follower_id(str(campaign_id), follower_id, 'done', str(datetime.now()))
    
    #send a message to a batch of followers, then their sent_time and status in the db
    def do_task(self):
        print('do_task')
        internet = False
        while not internet:
            try:
                followers_to_send = [ f for f in self.curr_followers if str(f['status']) == 'pending' ]
                for follower in followers_to_send:
                    self._send_message(follower)
                    self._mark_as_done(self.curr_campaign['id'], follower['follower_id'])
                internet = True
            except TweepError as e:
                print(e)
                if e.args[0][0]['code'] == 89:
                    self._auth = False
                    raise AuthFailureError(e)
                time.sleep(10)
            