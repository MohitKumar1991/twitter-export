from uuid import uuid4
from collections import OrderedDict, defaultdict
from .models import scopedsession,LogEvent, FollowerChanges,State, Followers, Campaign, CampaignFollowers, Link, Email
from sqlalchemy import func, text
import logging
from .utils import load_state
from datetime import datetime

def log_event(msg=''):
    logging.warn(msg) #just logging here also so i dont have to log two times
    le = LogEvent(msg=msg)
    scopedsession.add(le)
    scopedsession.commit()

def get_log_events(count=100):
    events = scopedsession.query(LogEvent).order_by(LogEvent.created_at.desc()).limit(count).all()
    return [ e.to_dict() for e in events ]

def get_new_and_unfollowed_followers(times=4):
    start_times = scopedsession.query(FollowerChanges.update_start_time).distinct(FollowerChanges.update_start_time).order_by(FollowerChanges.update_start_time.desc()).limit(times).all()
    fchanges = scopedsession.query(FollowerChanges).filter(FollowerChanges.update_start_time.in_(start_times)).all()
    new_followers = []
    unfollowed_followers = []
    for fc in fchanges:
        if fc.change_type == 'new':
            new_followers.append(fc.id)
        elif fc.change_type == 'unfollow':
            unfollowed_followers.append(fc.id)
        else:
            logging.warn(f'found unknown change_type {fc.change_type} for {fc.id}')
    return {'new': new_followers, 'unfollowed': unfollowed_followers }

def compute_unfollowed_and_new_followers():
    state = load_state()
    update_start = datetime.fromtimestamp(state['last_update_start_ms']/1000)
    update_start_ms = state['last_update_start_ms']
    new_followers = scopedsession.query(Followers.id).filter(Followers.row_created_at > update_start).all()
    unfollowed_followers = scopedsession.query(Followers.id).filter(Followers.row_updated_at <  update_start).all()
    for f in new_followers:
        scopedsession.add(FollowerChanges(follower_id=f.id,change_type='new', update_start_time=update_start_ms))
    for f in unfollowed_followers:
        scopedsession.add(FollowerChanges(follower_id=f.id,change_type='unfollowed', update_start_time=update_start_ms))
    return { 'new':new_followers, 'unfollowed': unfollowed_followers }

def get_follower_changes(count=300):
    fcs = scopedsession.query(FollowerChanges).order_by(FollowerChanges.created_at.desc()).limit(count).all()
    return [ fc.to_dict() for fc in fcs ]

def get_followers_count_with_query(query=None):
    if query is not None:
        return query
    followers_count = scopedsession.query(Followers.id).count()
    return followers_count

def get_followers_with_query(query):
    q = text('select * from all_followers ' + query)
    try:
        followers = scopedsession.query(Followers).from_statement(q)
        scopedsession.commit()
    except:
        scopedsession.rollback()
    return [ f.to_dict() for f in followers ]

def get_one_follower(follower_id):
    follower = scopedsession.query(Followers).get(follower_id)
    if follower is not None:
        return follower.to_dict()

def get_followers(follower_ids=None):
    if follower_ids is None:
        followers = scopedsession.query(Followers).all()
    else:
        follower_ids = tuple(follower_ids)
        followers = scopedsession.query(Followers).filter(Followers.id.in_(follower_ids)).all()
        logging.debug(f'get_followers total {len(follower_ids)} followers')
    return [ f.to_dict() for f in followers ]

def get_all_followers(campaign_id):
    cf = scopedsession.query(CampaignFollowers).filter(CampaignFollowers.campaign_id == campaign_id).all()
    return [ c.to_dict() for c in cf ]

def create_campaign(campaign_details, followers):
    campaign = Campaign()
    campaign.status = 'pending'
    campaign.name = campaign_details['name']
    campaign.message_template = campaign_details['message_template']
    campaign.last_run = None
    scopedsession.add(campaign)
    scopedsession.commit()
    return campaign.id

def delete_campaign(campaign_id):
    scopedsession.query(Campaign).filter(Campaign.id == campaign_id).delete()
    scopedsession.commit()

def get_all_campaigns():
    campaigns = scopedsession.query(Campaign).order_by(Campaign.status).all()
    campaign_followers = scopedsession.query(CampaignFollowers.campaign_id, func.count(CampaignFollowers.campaign_follower_id)).group_by(CampaignFollowers.campaign_id).all()
    cf_index = defaultdict()
    for cf in campaign_followers:
        cf_index[cf[0]] = cf[1]
    result = []
    for c in campaigns:
        d = c.to_dict()
        d['followers_count'] = cf_index[d['id']]
        result.append(d)
    return result

def get_current_campaign():
    campaign = scopedsession.query(Campaign).filter(Campaign.status =="active").first()
    if campaign is not None:
        return campaign.to_dict()
    else:
        return None

def change_campaign_status(campaign_id, status):
    cc = scopedsession.query(Campaign).filter(Campaign.id == campaign_id).update({'status': status})
    scopedsession.commit()
    return cc

def get_pending_campaigns():
    cc = scopedsession.query(Campaign).filter(Campaign.status == 'pending').all()
    return [ c.to_dict() for c in cc ]

def get_all_followers_status(campaign_id):
    cf = scopedsession.query(CampaignFollowers).filter(CampaignFollowers.campaign_id == campaign_id).all()
    return [ c.to_dict() for c in cf ]


def get_campaign_follower_details(campaign_id):
    follower_statuses = get_all_followers_status(campaign_id)
    follower_index = {}
    for fs in follower_statuses:
        follower_index[fs['follower_id']] = fs
    follower_ids = follower_index.keys()
    followers = get_followers(follower_ids)
    for follower in followers:
        follower['status'] = follower_index.get(follower['id'], { 'status':None })['status']
        follower['sent_time'] = follower_index.get(follower['id'], {'sent_time': None })['sent_time']
    return followers

def update_campaign_follower(cf):
    scopedsession.merge(CampaignFollowers(**cf))
    scopedsession.commit()

def update_follower_id(campaign_id, follower_id, status, sent_time):
    pid = campaign_id + '_' +follower_id
    cf = CampaignFollowers(campaign_follower_id=pid,campaign_id=campaign_id, follower_id=follower_id,status=status,sent_time=sent_time)
    scopedsession.merge(cf)
    scopedsession.commit()

def insert_campaign_followers(campaign_id, follower_ids):
    for follower_id in follower_ids:
        cf = CampaignFollowers(**{'campaign_follower_id': str(campaign_id) + '_' + str(follower_id), 'campaign_id': campaign_id, 'follower_id': str(follower_id), 'status': 'pending' })
        scopedsession.add(cf)
    scopedsession.commit()

def get_campaign_details(campaign_id):
    campaign = scopedsession.query(Campaign).get(campaign_id)
    if campaign is None:
        return None
    campaign = campaign.to_dict()
    campaign_followers = get_campaign_follower_details(campaign_id)
    campaign['followers'] = campaign_followers
    return campaign

def create_link(created_by, parent_link_id):
    new_link = Link()
    if parent_link_id is not None:
        link = scopedsession.query(Link).filter_by(id=parent_link_id).first()
        new_link.parent_link_id = link.id
        if link.root_link_id is None:
            new_link.root_link_id = link.id #this link is the root link
            original_user = link.created_by
        else:
            root_link = scopedsession.query(Link).filter_by(id=link.root_link_id).first()
            new_link.root_link_id = root_link.id
            original_user = root_link.created_by
    else:
        new_link.parent_link = None
        new_link.root_link = None
        original_user = created_by #new link this is root

    url = Link.url_from_username(original_user, created_by)
    new_link.url = url
    new_link.desc = f"af link by {created_by}"
    new_link.created_by = created_by

    scopedsession.add(new_link)
    scopedsession.commit()
    new_link = scopedsession.query(Link).filter_by(url=url).first()
    return new_link

def get_all_links():
    links = scopedsession.query(Link).all()
    return [l.to_dict() for l in links]

def get_link(**kwargs):
    link = scopedsession.query(Link).filter_by(**kwargs).first()
    return link

def get_all_links_created_by(created_by):
    original_links = scopedsession.query(Link).filter_by(created_by=created_by).all()
    all_links = []
    parent_links = original_links
    while parent_links is not None and len(parent_links) > 0:
        all_links = all_links + parent_links
        parent_links_ids = ( l.id for l in parent_links )
        next_links = scopedsession.query(Link).filter(Link.parent_link_id.in_(parent_links_ids)).all()
        parent_links = next_links
    return all_links

def get_emails_for_links_ids(all_links_ids):
    emails = scopedsession.query(Email).filter(Email.parent_link_id.in_(all_links_ids)).all()
    return [ e.to_dict() for e in emails ]

def create_email(params):
    new_submit = Email(**params)
    scopedsession.add(new_submit)
    scopedsession.commit()
    return new_submit

def get_all_emails():
    emails = scopedsession.query(Email).all()
    return [ e.to_dict() for e in emails ]

    