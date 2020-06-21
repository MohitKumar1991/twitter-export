import sqlite3
conn = sqlite3.connect('main.db')
from enum import Enum

class FState(Enum):
    CREATING = 'CREATING'
    READY = 'READY'
    UPDATING = 'UPDATING'

def init_campaign_db(db_obj):
    cursor = db_obj.cursor()
    cursor.execute(''' create table curr_state_table (
                                                    key text primary key, 
                                                    value text
                                                )''')
    cursor.execute(''' create table campaigns (
                                                    id text primary key, 
                                                    name text,
                                                    status text,
                                                    message_template text,
                                                    last_run text
                                                )''')
    
    cursor.execute(''' create table campaign_followers (
                                                    campaign_follower_id text primary key,
                                                    campaign_id text, 
                                                    follower_id text,
                                                    status text,
                                                    sent_time text
                                                )''')

    db_obj.commit()

def init_state_db(db_obj):
    cursor = db_obj.cursor()
    cursor.execute(''' create table curr_state_table ( key text primary key, value text  )''')
    db_obj.commit()

def init_followers_db(db_obj, username):
    cursor = db_obj.cursor()
    cursor.execute(''' CREATE TABLE all_followers (id int primary key, 
                                                id_str text, 
                                                name text,
                                                screen_name text, 
                                                location text, 
                                                description text, 
                                                url text, 
                                                entities text, 
                                                protected int, 
                                                followers_count int, 
                                                friends_count int, 
                                                listed_count int, 
                                                created_at text, 
                                                favourites_count text, 
                                                utc_offset text, 
                                                time_zone text, 
                                                geo_enabled int, 
                                                verified int, 
                                                statuses_count int, 
                                                lang text, 
                                                contributors_enabled int, 
                                                is_translator int, 
                                                is_translation_enabled int, 
                                                profile_background_color text, 
                                                profile_background_image_url text, 
                                                profile_background_image_url_https text, 
                                                profile_background_tile text, 
                                                profile_image_url text, 
                                                profile_image_url_https text, 
                                                profile_banner_url text, 
                                                profile_link_color text, 
                                                profile_sidebar_border_color text, 
                                                profile_sidebar_fill_color text, 
                                                profile_text_color text, 
                                                profile_use_background_image text, 
                                                has_extended_profile text, 
                                                default_profile text, 
                                                default_profile_image text, 
                                                following int, 
                                                follow_request_sent int, 
                                                notifications int, 
                                                translator_type text
                                            );    ''')
    cursor.execute(''' create table curr_state_table (
                                                    key text primary key, 
                                                    value text
                                                )''')
    db_obj.commit()