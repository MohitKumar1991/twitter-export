from flask import url_for, Flask
from flask import request, redirect
from flask import Response, render_template
import signal, requests
import sqlite3
import json
from datetime import datetime
from collections import OrderedDict
from .mytweepy import twpy
from .utils import store_state, load_state, convert_to_csv
from .dbutils import get_campaign_follower_details, get_campaign_details, get_all_campaigns, create_campaign, insert_campaign_followers, delete_campaign, get_followers_with_query
from .dbutils import get_followers_count_with_query, create_link, get_all_links, get_link, get_all_links_created_by, get_emails_for_links_ids, create_email, get_all_emails

app = Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route("/email", methods=['GET'])
def subemails():
    state = load_state()
    return render_template('emails.html',username=state.get('username', ''))

#get all emails submitted for a particular user
@app.route("/emails", methods=["GET"])
def getemails():
    emails = get_all_emails()
    return Response(json.dumps(emails), mimetype='application/json', status=200)

#get all emails submitted for a particular user
@app.route("/state", methods=["GET"])
def currentstate():
    state = load_state()
    return Response(json.dumps(state), mimetype='application/json', status=200)

@app.route("/export", methods=['GET'])
def export():
    query = request.args.get('query', '')
    limit = request.args.get('limit', '')
    if len(query) > 0:
        query = 'WHERE ' + query
    if len(limit) > 0:
        limit = 'LIMIT ' + str(int(limit))  
    final_query =  query + ' ' + limit
    followers = get_followers_with_query(final_query)
    filename = 'followers_{0}.csv'.format(str(datetime.now()))
    is_done = convert_to_csv(filename, followers)
    if not is_done:
        return Response(json.dumps({'error': 'Could not export'}), mimetype='application/json', status=400) 
    return Response(json.dumps({'filename': filename}), mimetype='application/json')


@app.route("/campaigns", methods=['GET', 'POST', 'DELETE'])
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
    curr_status = load_state()
    curr_status.update(worker_status)
    return Response(json.dumps(curr_status), mimetype='application/json')

@app.route("/search", methods=['GET'])
def dashboard():
    username = load_state().get('username','')
    return render_template('main.html',username=username)

@app.route("/updates", methods=['GET'])
def updates():
    curr_status = load_state()
    fcount = get_followers_count_with_query('')
    return render_template('updates.html', **curr_status, fcount=fcount)

@app.route("/auth", methods=['GET'])
def auth():
    curr_state = load_state()
    return render_template('auth.html', **{ 'consumer_key':  curr_state.get('CONSUMER_KEY', None), 'consumer_secret': curr_state.get('CONSUMER_SECRET_KEY', None) })

@app.route("/auth_pin", methods=['GET'])
def auth_pin():
    pin = request.args.get('pin', None)
    if not pin:
        return Response(json.dumps({'error': 'No Pin'}), mimetype='application/json', status=400)
    import tweepy
    from tweepy.error import TweepError
    try:
        twpy.set_pin_and_init(pin)
    except TweepError as te:
        print(te)
        return Response(json.dumps({ 'error':str(te) }), mimetype='application/json', status=400)
    return Response(json.dumps({'success': 'true' }), mimetype='application/json')


@app.route("/auth_link", methods=['GET'])
def auth_link():
    consumer_key = request.args.get('consumer_key', None)
    consumer_secret = request.args.get('consumer_secret', None)
    if consumer_key is None or consumer_secret is None:
        return Response(json.dumps({'error': True}), mimetype='application/json', status=400)
    
    auth_url = twpy.init_oauth(consumer_key, consumer_secret)
    if auth_url is None:
        return Response(json.dumps({ 'error':'failed' }), mimetype='application/json', status=400)
        
    store_state({   
                    'CONSUMER_KEY':consumer_key, 
                    'CONSUMER_SECRET_KEY':consumer_secret 
                })
    return Response(json.dumps({'auth_url': auth_url}), mimetype='application/json')


# function that is called when you visit /
@app.route("/link", methods=["GET"])
def index():
    # just show a nice page saying what this is
    return render_template('link.html')

# create new af link - takes either the username of the person or another af link
@app.route("/links", methods=["GET"])
def alllinks():
    links = get_all_links()
    return Response(json.dumps(links), mimetype='application/json', status=200)

# create new af link - takes either the username of the person or another af link
@app.route("/link", methods=["POST"])
def createlink():
    body = request.json
    
    if 'created_by' not in body:
        state = load_state()
        created_by = state.get('username')
    else:
        created_by = body.get('created_by')
    original_user = None
    #username is who is generating the link once he submits email
    if 'parent_link_id' in body and len(body['parent_link_id']) > 0:
        link_id = body['parent_link_id']
    else:
        link_id = None

    new_link = create_link(created_by, link_id)
    return Response(json.dumps(new_link.to_dict()), mimetype='application/json', status=200)

# take email and the link for which the email was submitted
@app.route("/email", methods=["POST"])
def email():
    body = request.json
    if 'email' not in body or 'link_id' not in body or 'username' not in body:
        return Response(json.dumps({'error': 'need both email and which link this email was given to' }), mimetype='application/json', status=400)
    link_id = body['link_id']
    link = get_link(id=int(link_id))
    submitted_email = create_email({
        'email': body.get('email'),
        'parent_link_id': link.id,
        'name': body.get('name','')
    })
    username =  body.get('username')
    # submitted_email = Email.query.filter_by(parent_link_id=link.id, email=email).first()
    aflink = create_link(username, link_id)
    return Response(json.dumps({ 'email': submitted_email.to_dict(), 'aflink': aflink.to_dict() }), mimetype='application/json', status=200)


#render the page to submit one's email
@app.route("/l/<linkurl>", methods=["GET"])
def rendersubmit(linkurl):
    link = get_link(url=linkurl)
    username = load_state().get('username')
    if link is None:
        return Response(json.dumps({'error': 'wrong link url' }), mimetype='application/json', status=404)
    return render_template('submit.html', link_id=link.id, username=username)


@app.route("/", methods=['GET'])
def rootpath():
    state = load_state()
    if state.get('is_auth','false') == 'true':
        return redirect('/updates')
    else:
        return redirect('/auth')





