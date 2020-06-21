def make_batches(lst,size):
    return [ lst[i:i+size] for i in range(0, len(lst), size) ]


def load_state(state_db) -> dict:
    result = {}
    c = state_db.cursor()
    c.execute(''' select * from curr_state_table ''')
    rows = c.fetchall()
    for row in rows:
        result[row[0]] = row[1]
    print('STATE LOADED', result)
    return result

def store_state(state_db, d:dict):
    c = state_db.cursor()
    for k in d:
        c.execute("insert or replace into curr_state_table (key, value) values (?,?)", (k, d[k]) )
    state_db.commit()
    return True

def store_state_worker(state_db_worker, d:dict):
    for k in d:
        state_db_worker.execute("insert or replace into curr_state_table (key, value) values (?,?)", (k, d[k]) )
    return True


def load_state_worker(state_db_worker) -> dict:
    result = {}
    rows = state_db_worker.execute(''' select * from curr_state_table ''')
    for row in rows:
        result[row[0]] = row[1]
    print('STATE LOADED', result)
    return result