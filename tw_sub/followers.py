from datetime import datetime, timedelta
import sqlite3, pandas as pd
import time, json, tweepy
from .utils import make_batches, load_state, store_state
from .config import get_tweepyapi, fdb, FOLLOWERS_DB, STATE_DB, reset_tweepyapi, USERNAME
from tweepy import RateLimitError, TweepError
from .errors import AuthFailureError
from collections import OrderedDict
import json
import threading

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
                                                "created_at", 
                                                "favourites_count", 
                                                "utc_offset", 
                                                "time_zone", 
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
                                                "translator_type"]

class FollowersTask:
    def __init__(self, stop_event=None):
        self.task_run = stop_event if stop_event is not None else threading.Event()
        self.db  = sqlite3.connect(FOLLOWERS_DB)
        state = load_state(self.db)
        self.last_run = datetime.strptime(state.get('last_run', '2010-06-16 23:57:08.027042'), '%Y-%m-%d %H:%M:%S.%f')
        self.index_status = state.get('index_status', 'INIT')
        next_cursor = state.get('next_cursor', None)
        next_cursor = None if next_cursor == '0' or next_cursor == 0 else next_cursor
        self.checkpoint = {
            'next_cursor': next_cursor
        }
        self.auth, self.tweepyapi = get_tweepyapi()
        self.username = USERNAME
        self.rate_limited = False
        self.curr_iterator = None

    def run(self):
        while not self.task_run.is_set():
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
            except StopIteration as si:
                if self.index_status == 'UPDATING' or self.index_status == 'CREATING':
                    self.index_status = 'READY'
            finally:
                self.last_run = datetime.now()
                self._create_checkpoint()
    
    def _wait_for_update(self):
        print("followers:: ",'_wait_for_update', self.index_status, (datetime.now() - self.last_run))
        if self.index_status == 'READY' and (datetime.now() - self.last_run) > timedelta(days=1):
            self.index_status = 'UPDATING'
        elif self.index_status == 'READY' and  (datetime.now() - self.last_run) < timedelta(days=1):
            time.sleep((datetime.now() - self.last_run).total_seconds())
            self.index_status = 'UPDATING'
        elif self.index_status == 'INIT':
            self.index_status = 'CREATING'
        #nothing for creating and updating

    def stop(self):
        self.task_run.set()
    
    def _wait_till_available(self):
        while True:
            state = load_state(self.db)
            self.index_status = state.get('index_status', 'CREATING')
            self.auth, self.tweepyapi = get_tweepyapi()
            if self.index_status == 'INIT':
                self.index_status = 'CREATING'
            if not self.auth:
                time.sleep(5)
                reset_tweepyapi()
            elif self.index_status == 'READY' or (self.rate_limited and (datetime.now() - self.last_run) < timedelta(minutes=15)):
                time.sleep(5)
            else:
                if self.curr_iterator is None: ##because need to wait for auth
                    self.curr_iterator = tweepy.Cursor(self.tweepyapi.followers_ids, screen_name=self.username, cursor=self.checkpoint['next_cursor']).pages()
                return

    def _create_checkpoint(self):
        print("followers:: ",'_create_checkpoint', self.checkpoint)
        store_state(self.db, {
            'next_cursor':  self.checkpoint['next_cursor'],
            'last_run': str(self.last_run),
            'index_status': self.index_status
        })
    
    def _save_data_in_db(self, data):
        cursor = self.db.cursor()
        for d in data:
            d = OrderedDict(d._json)
            k_to_remove = []
            for k in d:
                if k not in CURR_FIELDS:
                    k_to_remove.append(k)
            for k in k_to_remove:
                del d[k]
            d['entities'] = json.dumps(d['entities'])
            if 'status' in d:
                del d['status']
            columns = ', '.join(d.keys())
            placeholders = ':'+', :'.join(d.keys())
            query = 'INSERT OR REPLACE INTO all_followers (%s) VALUES (%s)' % (columns, placeholders)
            cursor.execute(query, d)
        self.db.commit()
    
    def do_task(self):
        print("followers:: ", 'do_task', self.curr_iterator.__dict__)
        internet = False
        while not internet:
            try:
                follow_ids = next(self.curr_iterator)
                internet = True
            except TweepError as e:
                print(e)
                time.sleep(10)
        user_results = []
        for btch in make_batches(follow_ids, 100):
            internet = False
            while not internet:
                try:
                    user_ids = self.tweepyapi.lookup_users(btch)
                    internet = True
                except TweepError as e:
                    print(e)
                    if e.args[0][0]['code'] == 89:
                        self._auth = False
                        raise AuthFailureError(e)
                    time.sleep(10)
            user_results = user_results + user_ids
        self._save_data_in_db(user_results)
        self.checkpoint['next_cursor'] = self.curr_iterator.next_cursor
        if int(self.checkpoint['next_cursor']) == 0:
            raise StopIteration('Next Cursor is 0 now')
            