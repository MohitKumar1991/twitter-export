from .config import campaign_db_worker, fdb_worker
from uuid import uuid4
from collections import OrderedDict, defaultdict

def get_followers_count_with_query(query):
    followers = fdb_worker.execute("select count(*) from all_followers "+ query)
    return tuple(followers[0])[0]

def get_followers_with_query(query):
    followers = fdb_worker.execute("select * from all_followers "+ query)
    print('GET FOLLOWERS FINAL QUERY', query)
    if type(followers) == str:
        raise Exception(followers)
    result = []
    for f in followers:
        f_dict = {}
        for fr in f.keys():
            f_dict[fr] = f[fr]
        result.append(f_dict)
    return result

def get_one_follower(follower_id):
    followers = fdb_worker.execute("select * from all_followers where id=?", (follower_id,))
    print('GET FOLLOWERS FINAL QUERY', query)
    if type(followers) == str:
        print(followers)
        return None
    if len(followers) != 1:
        return None
    f = followers[0]
    f_dict = {}
    for fr in f.keys():
        f_dict[fr] = f[fr]
    return f_dict



def get_followers(follower_ids=None):
    if follower_ids is None:
        followers = fdb_worker.execute("select * from all_followers")
    else:
        followers = fdb_worker.execute("select * from all_followers where id IN (" + ",".join(follower_ids) + ")")
    result = []
    for f in followers:
        f_dict = {}
        for fr in f.keys():
            f_dict[fr] = f[fr]
        result.append(f_dict)
    return result

def create_campaign(campaign_details, followers):
    campaign_id = str(uuid4())
    campaign_details['id'] = campaign_id
    campaign_details['status'] = 'pending'
    d = OrderedDict(campaign_details)
    columns = ', '.join(d.keys())
    placeholders = ':'+', :'.join(d.keys())
    query = 'INSERT INTO campaigns (%s) VALUES (%s)' % (columns, placeholders)
    campaign_db_worker.execute(query, d)
    return campaign_id

def delete_campaign(campaign_id):
    campaign_db_worker.execute('UPDATE campaigns SET status="deleted" WHERE campaign_id=?', (campaign_id,))

def update_campaign(campaign_details):
    d = OrderedDict(campaign_details)
    columns = ', '.join(d.keys())
    placeholders = ':'+', :'.join(d.keys())
    query = 'INSERT OR REPLACE INTO campaigns (%s) VALUES (%s)' % (columns, placeholders)
    campaign_db_worker.execute(query, d)


def get_all_campaigns():
    campaigns = campaign_db_worker.execute("select * from campaigns order by status")
    campaign_followers = campaign_db_worker.execute('select campaign_id, count(*)  from campaign_followers group by campaign_id')
    print(campaign_followers)
    cf_index = defaultdict()
    for cf in campaign_followers:
        cf_index[cf[0]] = cf[1]
    print(campaigns)
    return [ { 'id': campaign[0], 'name': campaign[1] ,'status': campaign[2],'message_template': campaign[3],'last_run': campaign[4], 'followers_count': cf_index.get(campaign[0]) } for campaign in campaigns ]


def get_current_campaign():
    campaign = campaign_db_worker.execute("select * from campaigns where status = 'active'")
    print('get_current_campaign', campaign)
    if len(campaign)> 0:
        campaign = campaign[0]
        return { 'id': campaign[0], 'name': campaign[1] ,'status': campaign[2],'message_template': campaign[3],'last_run': campaign[4] }
    else:
        return None

def change_campaign_status(campaign_id, status):
    cc = campaign_db_worker.execute("update campaigns set status = ? where id =? ", (status, campaign_id))
    print(cc)
    return cc

def get_pending_campaigns():
    cc = campaign_db_worker.execute("select * from campaigns where status = 'pending'")
    return [ { 'id': campaign[0], 'name': campaign[1] ,'status': campaign[2],'message_template': campaign[3],'last_run': campaign[4] }  for campaign in cc ]

def get_all_followers(campaign_id):
    cf = campaign_db_worker.execute("select * from campaign_followers where campaign_id = ?", (campaign_id,))
    return [ { 
                'campaign_follower_id': c[0],
                'campaign_id': c[1],
                'follower_id': c[2],
                'status':c[3],
                'sent_time': c[4]           
              } for c in cf ]


def get_campaign_follower_details(campaign_id):
    follower_statuses = get_all_followers(campaign_id)
    follower_index = {}
    for fs in follower_statuses:
        follower_index[fs['follower_id']] = fs
    follower_ids = follower_index.keys()
    followers = get_followers(follower_index)
    for follower in followers:
        follower['status'] = follower_index.get(follower['id'], { 'status':None })['status']
        follower['sent_time'] = follower_index.get(follower['id'], {'sent_time': None })['sent_time']
    return followers

def update_campaign_follower(cf):
    d = OrderedDict(cf)
    columns = ', '.join(d.keys())
    placeholders = ':'+', :'.join(d.keys())
    query = 'INSERT OR REPLACE INTO campaign_followers (%s) VALUES (%s)' % (columns, placeholders)
    campaign_db_worker.execute(query, d)

def update_follower_id(campaign_id, follower_id, status, sent_time):
    result = campaign_db_worker.execute('UPDATE campaign_followers set status=?, sent_time=? where campaign_follower_id=?',(status, sent_time, campaign_id + '_' +follower_id))
    print('update_follower_id', campaign_id, follower_id, status, sent_time, result)

def insert_campaign_followers(campaign_id, follower_ids):
    for follower_id in follower_ids:
        update_campaign_follower({'campaign_follower_id': str(campaign_id) + '_' + str(follower_id), 'campaign_id': campaign_id, 'follower_id': str(follower_id), 'status': 'pending','sent_time': '' })


def get_campaign_db_worker():
    cc = campaign_db_worker.execute("select * from campaigns where status = curre ")


def get_campaign_details(campaign_id):
    campaign = campaign_db_worker.execute("select * from campaigns where id=?", (campaign_id, ))
    if len(campaign) > 0:
        campaign = campaign[0]
    else:
        return None
    campaign = { 'id': campaign[0], 'name': campaign[1] ,'status': campaign[2],'message_template': campaign[3],'last_run': campaign[4] }
    campaign_followers = get_campaign_follower_details(campaign_id)
    campaign['followers'] = campaign_followers
    return campaign
    