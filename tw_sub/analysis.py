import re, json
import logging

occupations = None
with open('./tw_sub/datasets/occupations.json', 'r') as f:
    occupations = json.load(f)
    occupations = occupations['occupations']
"""
 [[('marketing', {'marketing'}) ],
            [('investor', {'marketing specialist'})],
            []]
"""
def find_occupations(desc):
    if len(desc) == 0:
        return None
    desc = desc.lower()
    w = re.split(r'[,\.\s|_\-!/#*]', desc)
    w = [ wr for wr in w if len(wr.strip()) > 0]  #remove empty spaces
    ngrams = []
    ngrams.append(w)
    ngrams.append([ f'{w[i]} {w[i+1]}' for i in range(0, len(w) - 1) ])
    ngrams.append([ f'{w[i]} {w[i+1]} {w[i+2]}' for i in range(0, len(w) - 2) ])
    ngram_professions = []
    for ng in ngrams:
        professions = []
        for ocgrp in occupations:
            ng_set = set(ng)
            oc_set = set(occupations[ocgrp])
            found_set = oc_set.intersection(ng_set)
            if len(found_set)>0:
                professions.append((ocgrp, found_set))
        ngram_professions.append(professions)
    return ngram_professions

def find_followers_occupation(followers):
    result = []
    for f in followers:
        if len(f.description) > 0:
            try:
                professions = find_occupations(f.description)
                metadata = professions
                professions.reverse()
                pgrps = get_first_n_unique([ p_detected[0] for n_level in professions for p_detected in n_level ])
            except Exception as e:
                logging.exception(e)
                pgrps = []
        else:
            pgrps = []
        result.append((f.id, pgrps))
    return dict(result)

def get_first_n_unique(l, n=2):
    #only for 3.7 and above assumes order preserve
    ordered = dict([(le, 1) for le in l])
    return [*ordered.keys()][:n]
    

if __name__ == "__main__":
    import pprint
    from .models import Followers, scopedsession
    pp = pprint.PrettyPrinter(indent=4)
    followers = scopedsession.query(Followers).limit(3000).all()
    follower_occupation_df = find_followers_occupation(followers)
    pp.pprint(follower_occupation_df)

    