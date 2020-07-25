from .models import scopedsession, State
from typing import List
import os

def make_batches(lst,size):
    return [ lst[i:i+size] for i in range(0, len(lst), size) ]

def load_state() -> dict:
    state = scopedsession.query(State).all()
    result = {}
    for s in state:
        d = s.to_dict()
        result[d['key']] = d['value']
    return result

def store_state(d:dict):
    try:
        states = [ scopedsession.merge(State(key=k, value=str(d[k]))) for k in d ]
        scopedsession.commit()
    except:
        scopedsession.rollback()

def convert_to_csv(filename, data: List[dict]):
    if len(data) == 0:
        return False
    import csv
    fieldnames = data[0].keys()
    with open(os.path.join(os.path.dirname(__file__), 'static',filename), 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for d in data:
            writer.writerow(d)
    return True

def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time,datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff / 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff / 30) + " months ago"
    return str(day_diff / 365) + " years ago"


