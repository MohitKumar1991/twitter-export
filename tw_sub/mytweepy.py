from tweepy.error import TweepError
from .utils import load_state, store_state
import tweepy, json, logging
from .config import config
from .dbutils import log_event

class MyTweepy:
    def __init__(self):
        self.tweepyapi = None
        self.oauth = None
        self.username = None
    
    def try_init(self):
        state = load_state()
        logging.debug(f"trying to init tweepy...ck{state.get('CONSUMER_KEY', None)} csk {state.get('CONSUMER_SECRET_KEY', None)} uk ${state.get('USER_KEY',None)} usk {state.get('USER_SECRET', None)}")
        if state.get('CONSUMER_KEY', None) is not None and state.get('CONSUMER_SECRET_KEY', None) is not None:
            self.oauth = tweepy.OAuthHandler(state.get('CONSUMER_KEY'), state.get('CONSUMER_SECRET_KEY'))
            if state.get('USER_KEY',None) is not None and state.get('USER_SECRET', None) is not None:
                self.oauth.set_access_token(state.get('USER_KEY'), state.get('USER_SECRET'))
                self.tweepyapi = tweepy.API(self.oauth)
                try:
                    if len(config.TWITTER_USERNAME) > 0:
                        log_event(f'getting stuff for {config.TWITTER_USERNAME}')
                        myuser = self.tweepyapi.get_user(screen_name=config.TWITTER_USERNAME)
                        self.username =  myuser.screen_name
                    if self.username is None or len(config.TWITTER_USERNAME) == 0:
                        myuser = self.tweepyapi.me()
                        self.username =  myuser.screen_name 
                    store_state({ 'username': self.username, 'is_auth': 'true' })
                except TweepError as e:
                    logging.exception(e)
                    if str(e.api_code) == '89':
                        store_state({ 'username': '', 'is_auth': 'false' })
        else:
            store_state({ 'username': '', 'is_auth': 'false' })
    
    def init_oauth(self, consumerkey, consumersecret):
        try:
            self.oauth = tweepy.OAuthHandler(consumerkey, consumersecret, callback='oob')
            logging.debug(f'initing oauth to ${self.oauth}')
            return self.oauth.get_authorization_url()
        except TweepError as te:
            logging.exception(te)
            return None
    
    def set_pin_and_init(self, pin):
        try:
            user_key, user_secret = self.oauth.get_access_token(pin)
        except TweepError as te:
            logging.exception(te)
            raise te
        store_state({
                'USER_KEY': user_key,
                'USER_SECRET': user_secret
            })
        self.try_init()

    @property
    def is_auth(self):
        if self.tweepyapi is not None and self.oauth is not None:
            return True
        else:
            return False
    
    def clear_auth(self):
        self.tweepyapi = None

twpy = MyTweepy()
twpy.try_init()
        
        
        
        


    


    