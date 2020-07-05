from datetime import datetime, timedelta
from tweepy import RateLimitError, TweepError 
from .errors import AuthFailureError
import threading, logging
import time, json, tweepy
from jinja2 import Template
from .utils import make_batches, load_state
from .mytweepy import twpy
from .dbutils import get_one_follower, update_follower_id, get_pending_campaigns, change_campaign_status, get_current_campaign, get_all_followers

class CampaignsTask:
    def __init__(self, stop_event:threading.Event):
        self.stop_event = stop_event
        self.rate_limited = False
        self.curr_campaign = None
        self.curr_followers = None
        state = load_state()
        self.last_run = datetime.strptime(state.get('last_run', '2010-06-16 23:57:08.027042'), '%Y-%m-%d %H:%M:%S.%f')
        #if there is no campaign active then turn one into active

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
                logging.exception(rle)
                self.rate_limited = True
            except AuthFailureError as afe:
                logging.exception(afe)
                twpy.clear_auth()
                store_state({
                    'USER_KEY': '',
                    'USER_SECRET': ''
                })
                logging.debug('clearing auth info...')
            self._create_checkpoint()

    def _send_message(self, campaign_follower):
        #use jinja2 templating here
        t = Template(self.curr_campaign['message_template'])
        follower = get_one_follower(campaign_follower['follower_id'])
        if follower is None:
            logging.error('FOllowers with ID {} not found'.format(campaign_follower['follower_id']))
            return
        msg = t.render(follower=follower)
        logging.debug(f"sending message to {follower['name']}")
        twpy.tweepyapi.send_direct_message(str(follower['id']), msg)
        

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
        logging.debug(f"setting active campaign to {self.curr_campaign['name']} with {len(self.curr_followers)} followers")

    # wait for IS_AUTH, AN ACTIVE CAMPAIGN, RATE_LIMIT AND INTERNET
    def _wait_till_available(self):
        logging.debug(f"_wait_till_available campaign:{self.curr_campaign} rate:{self.rate_limited}")
        while True:
            #keep trying for this
            if not twpy.is_auth:
                twpy.try_init()
            if self.curr_campaign is None:
                self._ensure_current_active_campaign()
            if not twpy.is_auth or self.curr_campaign is None or (self.rate_limited and (datetime.now() - self.last_run) < timedelta(hours=1)):
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
        update_follower_id(str(campaign_id), follower_id, 'done', datetime.now())
    
    #send a message to a batch of followers, then their sent_time and status in the db
    def do_task(self):
        internet = False
        while not internet:
            try:
                followers_to_send = [ f for f in self.curr_followers if str(f['status']) == 'pending' ]
                logging.debug(f"total followers remaining to send {len(followers_to_send)} ")
                for follower in followers_to_send:
                    self._send_message(follower)
                    self._mark_as_done(self.curr_campaign['id'], follower['follower_id'])
                internet = True
            except TweepError as e:
                logging.exception(e)
                if e.args[0][0]['code'] == 89:
                    self._auth = False
                    raise AuthFailureError(e)
                time.sleep(10)
            