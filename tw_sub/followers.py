from datetime import datetime, timedelta
import time, json, tweepy
from .utils import make_batches, load_state, store_state
from .mytweepy import twpy 
from .models import scopedsession, Followers
from tweepy import RateLimitError, TweepError
from .errors import AuthFailureError
from .analysis import find_followers_occupation
from collections import OrderedDict
import json
import threading
import logging
from .dbutils import log_event

"""
INIT -> CREATING -> READY 
UPDATING -> READY

"""

CURR_FIELDS = [ "id",  "id_str", "name",  "screen_name",  "location", "description", 
                                                "url", 
                                                "entities", 
                                                "protected", 
                                                "followers_count", 
                                                "friends_count", 
                                                "listed_count", 
                                                "favourites_count", 
                                                "utc_offset", 
                                                "created_at",
                                                "time_zone", 
                                                "occupation1",
                                                "occupation2",
                                                "country",
                                                "geo_enabled", 
                                                "verified", 
                                                "statuses_count", 
                                                "lang", 
                                                "contributors_enabled", 
                                                "is_translator", 
                                                "is_translation_enabled", 
                                                "profile_background_color", 
                                                "profile_background_image_url", 
                                                "profile_background_image_url_https", 
                                                "profile_background_tile", 
                                                "profile_image_url", 
                                                "profile_image_url_https", 
                                                "profile_banner_url", 
                                                "profile_link_color", 
                                                "profile_sidebar_border_color", 
                                                "profile_sidebar_fill_color", 
                                                "profile_text_color", 
                                                "profile_use_background_image", 
                                                "has_extended_profile", 
                                                "default_profile", 
                                                "default_profile_image", 
                                                "following", 
                                                "follow_request_sent", 
                                                "notifications", 
                                                "translator_type",
                                                "change_diff",
                                                "row_created_at"]

class FollowersTask:
    def __init__(self, stop_event=None):
        self.task_run = stop_event if stop_event is not None else threading.Event()
        state = load_state()
        self.last_run = datetime.strptime(state.get('last_run', '2010-06-16 23:57:08.027042'), '%Y-%m-%d %H:%M:%S.%f')
        self.index_status = state.get('index_status', 'INIT')
        next_cursor = state.get('next_cursor', None)
        next_cursor = None if next_cursor == '0' or next_cursor == 0 else next_cursor
        self.checkpoint = {
            'next_cursor': next_cursor
        }
        logging.warn(f'initing - the current state is {self.last_run} {next_cursor}')
        self.twpy = twpy
        self.setup = False
        self.rate_limited = False
        self.curr_iterator = None

    def run(self):
        while not self.task_run.is_set():
            self._wait_till_available()
            try:
                self.do_task()
                self.rate_limited = False
            except RateLimitError as rle:
                loggin.exception(rle)
                logging.warn('got ratelimited waiting 5 mins')
                self.rate_limited = True
            except AuthFailureError as afe:
                twpy.clear_auth()
                store_state({
                    'USER_KEY': '',
                    'USER_SECRET': ''
                })
            except StopIteration as si:
                logging.exception(si)
                if self.index_status == 'UPDATING' or self.index_status == 'CREATING':
                    log_event(f'index was {self.index_status} now setting to READY')
                    self.index_status = 'READY'
                logging.warn(f'cursor has reached the end - index_status is now {self.index_status}')
                time.sleep(5)
            finally:
                self.last_run = datetime.now()
                self._create_checkpoint()

    def stop(self):
        self.task_run.set()
    
    
    """
    Assumptions
    1. This is running in the background
    2. Index is READY - Log exact times for the when the index is done
    """
    def _wait_till_available(self):
        logging.warn(f'wait_till_available last_run:{self.last_run} status:{self.index_status} twpy:{self.twpy.is_auth}')
        while True:
            state = load_state()
            ##try to init state all the time
            self.index_status = state.get('index_status', 'CREATING')
            if self.index_status == 'INIT':
                self.index_status = 'CREATING'
            if not self.twpy.is_auth:
                logging.warn(f'twpy is not initialized yet, trying init')
                self.twpy.try_init()
                time.sleep(2)
                continue
            if self.curr_iterator is None: ##because need to wait for auth
                logging.warn(f'wait_till_available initing curr_iterator')
                self.curr_iterator = tweepy.Cursor(self.twpy.tweepyapi.followers_ids, screen_name=self.twpy.username, cursor=self.checkpoint['next_cursor']).pages()
            
            if self.setup == False:
                self.setup = True
                log_event(f'everything is setup - index:{self.index_status}')

            ##ok things are setup
            logging.warn(f'wait_till_available timepassed since last run is {(datetime.now() - self.last_run)}')
            if self.index_status == 'READY':
                if (datetime.now() - self.last_run) > timedelta(hours=23):
                    self.index_status = 'UPDATING'
                    log_event(f'starting update of followers index:{self.last_run}')
                else:
                    logging.warn(f'wait_till_available index ready - idle....')
                time.sleep(5)
            elif self.rate_limited and (datetime.now() - self.last_run) < timedelta(minutes=5):
                time.sleep(5)
            else:
                return

    def _create_checkpoint(self):
        logging.warn(f'creating_checkpoint {self.checkpoint["next_cursor"]} twpy:{self.last_run} {self.index_status}')
        store_state({
            'next_cursor':  self.checkpoint['next_cursor'],
            'last_run': str(self.last_run),
            'index_status': self.index_status
        })
    
    """
    This will now first fetch the existing followers
    If found it will first look for followers
    1. Compute the diff for followers
     - description
     - name
     - screen_name
     - real url
    2. Add the new followers
    """
    def _save_in_db(self, data):
        occupations = find_followers_occupation(data)
        for d in data:
            d = d._json
            occ = occupations[d['id']]
            k_to_remove = []
            for k in d:
                if k not in CURR_FIELDS:
                    k_to_remove.append(k)
            for k in k_to_remove:
                del d[k]
            d['id'] = str(d['id'])
            #use this to get the actual url
            d['entities'] = json.dumps(d['entities'])
            if 'status' in d:
                del d['status']
            if len(occ) > 0:
                d['occupation1'] = occ[0]
                if len(occ) > 1:
                    d['occupation2'] = occ[1]
            scopedsession.merge(Followers(**d))
        scopedsession.commit()
        log_event(f"_save_in_db saved followers:{len(data)} for checkpoint:{self.checkpoint['next_cursor']}")
    
    def do_task(self):
        internet = False
        while not internet:
            try:
                follow_ids = next(self.curr_iterator)
                logging.warn(f'do_task got {len(follow_ids)} followers')
                internet = True
            except TweepError as e:
                logging.exception(e)
                time.sleep(10)
        user_results = []
        for btch in make_batches(follow_ids, 100):
            internet = False
            while not internet:
                try:
                    user_ids = self.twpy.tweepyapi.lookup_users(btch)
                    internet = True
                except TweepError as e:
                    logging.exception(e)
                    logging.warn(f'tweep error e.args is {json.dumps(e.args)}')
                    if str(e.api_code) == '89':
                        twpy.clear_auth()
                        raise AuthFailureError(e)
                    time.sleep(10)
            user_results = user_results + user_ids
        self._save_in_db(user_results)
        self.checkpoint['next_cursor'] = self.curr_iterator.next_cursor
        logging.warn(f'updating checkpoint to {self.checkpoint["next_cursor"]}')
        if int(self.checkpoint['next_cursor']) == 0:
            raise StopIteration('Next Cursor is 0 now')
            