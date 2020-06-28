from flask import url_for, Flask
from flask import request, redirect
from flask import Response, render_template
import signal, requests
import sqlite3
import json
from datetime import datetime
from collections import OrderedDict
from .config import MODE, state_db_worker, fdb, fdb_worker, reset_tweepyapi, IS_AUTH, FOLLOWERS_DB
from .utils import store_state_worker, load_state_worker
from .campdb import get_campaign_follower_details, get_campaign_details, get_all_campaigns, create_campaign, insert_campaign_followers, update_campaign, delete_campaign, get_followers_with_query
from .campdb import get_followers_count_with_query

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

tweepyOauthHander = None

SITE_NAME = 'https://twitter-export.herokuapp.com/'

@app.route("/proxy/<path:path>",methods=['GET','POST','DELETE'])
def proxy(path):
    global SITE_NAME
    if request.method=='GET':
        resp = requests.get(f'{SITE_NAME}{path}',params=request.args)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in  resp.raw.headers.items() if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)
        return response
    elif request.method=='POST':
        resp = requests.post(f'{SITE_NAME}{path}',json=request.get_json())
        print('RETURNED', f'{SITE_NAME}{path}', request.get_json(), resp.content)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)
        return response
    elif request.method=='DELETE':
        resp = requests.delete(f'{SITE_NAME}{path}').content
        response = Response(resp.content, resp.status_code, headers)
        return response

@app.route("/emails", methods=['GET'])
def subemails():
    from .config import USERNAME
    return render_template('emails.html',username=USERNAME)

@app.route("/export", methods=['GET'])
def export():
    con = sqlite3.connect(FOLLOWERS_DB)
    query = request.args.get('query', '')
    limit = request.args.get('limit', '')
    if len(query) > 0:
        query = 'WHERE ' + query
    if len(limit) > 0:
        limit = 'LIMIT ' + str(int(limit))
    final_query = "SELECT * from all_followers " +  query + ' ' + limit
    import pandas as pd
    df = pd.read_sql_query(final_query, con)
    filename = 'followers_{0}.csv'.format(str(datetime.now()))
    df.to_csv(filename, index=False)
    return Response(json.dumps({'filename': filename}), mimetype='application/json')


@app.route("/campaigns", methods=['GET', 'POST', 'PATCH', 'DELETE'])
def campaigns():
    if request.method == 'GET':
        campaign_id = request.args.get('campaign_id',None)
        if campaign_id is not None:
            campaign = get_campaign_details(campaign_id)
            return Response(json.dumps(campaign), mimetype='application/json')
        else:
            campaigns = get_all_campaigns()
            return Response(json.dumps(campaigns), mimetype='application/json')

    elif request.method == 'POST':
        body = request.json
        message_template = body.get('message_template', None)
        campaign_name = body.get('name', None)
        followers = body.get('followers', None)
        if message_template is None or campaign_name is None or followers is None:
            return Response(json.dumps({'error': 'Send all params properly'}), mimetype='application/json', status=400) 
        campaign_id = create_campaign({
            'name':campaign_name,
            'message_template':message_template
        }, followers)
        insert_campaign_followers(campaign_id, followers)
        return Response(json.dumps({ 'campaign_id': campaign_id }), mimetype='application/json')
    
    elif request.method == 'PATCH':
        body = request.json
        message = body.get('message_template', None)
        campaign_name = body.get('campaign_name', None)
        campaign_id = body.get('campaign_id')
        campaign_details = get_campaign_details(campaign_id)
        del campaign_details['followers']
        campaign_details.update(body)
        update_campaign(campaign_details)
        return Response(json.dumps(campaign_details), mimetype='application/json')
    
    elif request.method == 'DELETE':
        campaign_id = request.args.get('campaign_id',None)
        delete_campaign(campaign_id)
        return Response(json.dumps({'campaign_id': campaign_id}), mimetype='application/json')
    else:
        raise Exception('Wrong Method')

@app.route("/campaign_followers", methods=['GET'])
def campaign_followers():
    campaign_id = request.args.get('campaign_id',None)
    if campaign_id is not None:
        campaign_followers = get_campaign_follower_details(campaign_id)
        return Response(json.dumps(campaign_followers), mimetype='application/json')

@app.route('/followers', methods=['GET'])
def followers():
    query = request.args.get('query', '')
    limit = request.args.get('limit', '')

    if len(query) > 0:
        query = 'WHERE ' + query
    if len(limit) == 0:
        limit = 'LIMIT 2000'
    else:
        limit = 'LIMIT ' + str(int(limit)) #to make sure it is an int
    try:
        followers = get_followers_with_query(query + ' ' + limit)
        total = get_followers_count_with_query(query)
        return Response(json.dumps({'total':total, 'followers':followers}), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({'error': str(e)}), mimetype='application/json', status=400)
    

@app.route('/status', methods=['GET'])
def followers_status():
    worker_status = { 'runner_status': True, 'followers_status':  'stopped', 'campaigns_status': 'stopped' }
    curr_status = load_state_worker(fdb_worker)
    curr_status.update(worker_status)
    return Response(json.dumps(curr_status), mimetype='application/json')

@app.route("/search", methods=['GET'])
def dashboard():
    from .config import USERNAME
    return render_template('main.html',username=USERNAME)

@app.route("/updates", methods=['GET'])
def updates():
    curr_status = load_state_worker(fdb_worker)
    fcount = get_followers_count_with_query('')
    return render_template('updates.html', **curr_status, fcount=fcount)

@app.route("/auth", methods=['GET'])
def auth():
    curr_state = load_state_worker(state_db_worker)
    return render_template('auth.html', **{ 'consumer_key':  curr_state.get('CONSUMER_KEY', None), 'consumer_secret': curr_state.get('CONSUMER_SECRET_KEY', None) })

@app.route("/auth_pin", methods=['GET'])
def auth_pin():
    pin = request.args.get('pin', None)
    if not pin:
        return Response(json.dumps({'error': 'No Pin'}), mimetype='application/json', status=400)
    import tweepy
    from tweepy.error import TweepError
    try:
        user_key, user_secret = tweepyOauthHander.get_access_token(pin)
    except TweepError as te:
        print(te)
        return Response(json.dumps({ 'error':str(te) }), mimetype='application/json', status=400)
    store_state_worker(state_db_worker, {'USER_KEY': user_key, 'USER_SECRET': user_secret})
    reset_tweepyapi()

    return Response(json.dumps({'user_key': user_key, 'user_secret': user_secret }), mimetype='application/json')


@app.route("/auth_link", methods=['GET'])
def auth_link():
    global tweepyOauthHander
    consumer_key = request.args.get('consumer_key', None)
    consumer_secret = request.args.get('consumer_secret', None)
    if consumer_key is None or consumer_secret is None:
        return Response(json.dumps({'error': True}), mimetype='application/json', status=400)
    import tweepy
    from tweepy.error import TweepError
    try:
        tweepyOauthHander = tweepy.OAuthHandler(consumer_key, consumer_secret, callback='oob')
        auth_url = tweepyOauthHander.get_authorization_url()
    except TweepError as te:
        print(te)
        return Response(json.dumps({ 'error':str(te) }), mimetype='application/json', status=400)
    store_state_worker(state_db_worker, { 'CONSUMER_KEY':consumer_key, 
                            'CONSUMER_SECRET_KEY':consumer_secret 
                        })
    return Response(json.dumps({'auth_url': auth_url}), mimetype='application/json')

@app.route("/", methods=['GET'])
def rootpath():
    if IS_AUTH:
        return redirect('/updates')
    else:
        return redirect('/auth')

# def shutdown(sig, stackframe):
#     print("SHUTTING DOWN")


# signal.signal(signal.SIGINT, shutdown)

