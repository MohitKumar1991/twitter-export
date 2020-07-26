from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.types import Date
from sqlalchemy.sql import func
import datetime, time
from .config import config
from base64 import b64encode, b64decode

engine = create_engine(config.SQLALCHEMY_DATABASE_URI, connect_args=config.SQLALCHEMY_CONNECT_ARGS)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

scopedsession = scoped_session(SessionLocal)

class DictMixIn:
    def to_dict(self):
        return {
            column.name: getattr(self, column.name)
            if not isinstance(
                getattr(self, column.name), (datetime.datetime, datetime.date)
            )
            else getattr(self, column.name).isoformat()
            for column in self.__table__.columns
        }

class State(Base, DictMixIn):
    __tablename__ = "curr_state_table"

    key = Column(String, primary_key=True, index=True)
    value = Column(String)

class LogEvent(Base, DictMixIn):
    __tablename__ = "log_events"
    id = Column(Integer, primary_key=True, index=True)
    msg = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now)

class Campaign(Base, DictMixIn):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    status = Column(String)
    message_template = Column(String)
    last_run = Column(Date)

class CampaignFollowers(Base, DictMixIn):
    __tablename__ = "campaign_followers"

    campaign_follower_id = Column(String, primary_key=True, index=True)
    campaign_id = Column(Integer)
    follower_id = Column(String)
    status = Column(String)
    sent_time = Column(Date)

class Followers(Base, DictMixIn):
    __tablename__ = "all_followers"

    id = Column(String, primary_key=True, index=True)
    id_str = Column(String)
    name = Column(String)
    screen_name = Column(String)
    location = Column(String)
    #I havent thought about search properly so I will only limit occupations to 2
    occupation1 = Column(String, nullable=True)
    occupation2 = Column(String, nullable=True)
    country = Column(String, nullable=True)
    description = Column(String)
    url = Column(String)
    entities = Column(String)
    protected = Column(String)
    followers_count = Column(Integer)
    friends_count = Column(Integer)
    listed_count = Column(Integer)
    created_at = Column(String)
    favourites_count = Column(Integer)
    utc_offset = Column(String)
    time_zone = Column(String)
    geo_enabled = Column(String)
    verified = Column(String)
    statuses_count = Column(Integer)
    lang = Column(String)
    contributors_enabled = Column(String)
    is_translator = Column(String)
    is_translation_enabled = Column(String)
    profile_background_color = Column(String)
    profile_background_image_url = Column(String)
    profile_background_image_url_https = Column(String)
    profile_background_tile = Column(String)
    profile_image_url = Column(String)
    profile_image_url_https = Column(String)
    profile_banner_url = Column(String)
    profile_link_color = Column(String)
    profile_sidebar_border_color = Column(String)
    profile_sidebar_fill_color = Column(String)
    profile_text_color = Column(String)
    profile_use_background_image = Column(String)
    has_extended_profile = Column(String)
    default_profile = Column(String)
    default_profile_image = Column(String)
    following = Column(String)
    follow_request_sent = Column(String)
    notifications = Column(String)
    translator_type = Column(String)
    change_diff = Column(String, default="{}")
    row_created_at = Column(DateTime(timezone=True), default=datetime.datetime.now)
    row_updated_at = Column(DateTime(timezone=True), onupdate=datetime.datetime.now, default=datetime.datetime.now)


class FollowerChanges(Base, DictMixIn):
    __tablename__ = "follower_changes"
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(String)
    change_type = Column(String)
    update_start_time = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now)

# Note that we use sqlite for our tests, so you can't use Postgres Arrays
class Email(Base, DictMixIn):
    """Email Table."""

    __tablename__ = "email"

    id = Column(Integer, unique=True, primary_key=True)
    email = Column(String, nullable=False)
    name = Column(String, nullable=False)
    parent_link_id = Column(
        Integer, ForeignKey("link.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self):
        return f"<Email {self.email}>"


class Link(Base, DictMixIn):
    __tablename__ = "link"

    id = Column(Integer, unique=True, primary_key=True)
    desc = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    parent_link_id = Column( Integer, ForeignKey("link.id", ondelete="SET NULL"), nullable=True)
    root_link_id = Column( Integer, ForeignKey("link.id", ondelete="SET NULL"), nullable=True )
    created_by = Column(String, nullable=False) #person who is sending
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    @staticmethod
    def url_from_username(cls, root_created_by, created_by=None):
        unique_str = str(time.time())
        return b64encode(unique_str.encode('utf-8')).decode('utf-8').replace('=','')


    def __repr__(self):
        return f"<Link {self.id} {self.desc} by {self.created_by}>"
