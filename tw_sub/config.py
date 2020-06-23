import sqlite3, tweepy, os
from sqlite3worker import Sqlite3Worker
from .db import init_followers_db, init_campaign_db, init_state_db
from .utils import load_state, store_state, load_state_worker
from tweepy.error import TweepError

MODE = os.environ.get('MODE','ALL') #ALL, SERVER, INDEX

FOLLOWERS_DB = 'followers.db'
CAMPAIGN_DB = 'campaign.db'
STATE_DB = 'state.db'
USERNAME = ''

if not os.path.isfile(STATE_DB):
    state_db = sqlite3.connect(STATE_DB)
    init_state_db(state_db)
    state_db_worker = Sqlite3Worker(STATE_DB)
else:
    state_db = sqlite3.connect(STATE_DB)
    state_db_worker = Sqlite3Worker(STATE_DB)

curr_state = load_state(state_db)

_auth = None
tweepyapi = None
IS_AUTH = False

def reset_tweepyapi():
    global IS_AUTH, tweepyapi, _auth, state_db_worker
    curr_state = load_state_worker(state_db_worker)
    if 'CONSUMER_KEY' in curr_state and 'CONSUMER_SECRET_KEY' in curr_state:
        _auth = tweepy.OAuthHandler(curr_state['CONSUMER_KEY'], curr_state['CONSUMER_SECRET_KEY'])

    if _auth is not None and 'USER_KEY' in curr_state and 'USER_SECRET' in curr_state:
        _auth.set_access_token(curr_state['USER_KEY'], curr_state['USER_SECRET'])
        tweepyapi = tweepy.API(_auth)
        try:
            myuser = tweepyapi.me()
            IS_AUTH = True
            USERNAME = myuser.screen_name #'balajis'
            return True
        except TweepError as e:
            print(e)
            if e.args[0][0]['code'] == 89:
                IS_AUTH = False
            else:
                raise e
            return False
    return tweepyapi

reset_tweepyapi()

def get_tweepyapi():
    return IS_AUTH, tweepyapi
    
if not os.path.isfile(FOLLOWERS_DB):
    print('INITING FOLLOWERS DB')
    fdb = sqlite3.connect(FOLLOWERS_DB)
    init_followers_db(fdb, USERNAME)
    fdb_worker = Sqlite3Worker(FOLLOWERS_DB)
else:
    fdb = sqlite3.connect(FOLLOWERS_DB)
    fdb_worker = Sqlite3Worker(FOLLOWERS_DB)

#Monkey Patching
fdb_worker._sqlite3_conn.row_factory = sqlite3.Row
fdb_worker._sqlite3_cursor = fdb_worker._sqlite3_conn.cursor()


if not os.path.isfile(CAMPAIGN_DB):
    campaign_db = sqlite3.connect(CAMPAIGN_DB)
    init_campaign_db(campaign_db)
    campaign_db_worker = Sqlite3Worker(CAMPAIGN_DB)
else:
    campaign_db = sqlite3.connect(CAMPAIGN_DB)
    campaign_db_worker = Sqlite3Worker(CAMPAIGN_DB)


#TODO - Create flow for generating the keys





