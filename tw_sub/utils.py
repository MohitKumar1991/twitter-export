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
    states = [ scopedsession.merge(State(key=k, value=d[k])) for k in d ]
    scopedsession.commit()

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


