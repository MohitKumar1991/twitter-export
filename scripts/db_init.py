import sqlite3

conn = sqlite3.connect('./main.db')
# fconn = sqlite3.connect('followers.db')

c = conn.cursor()
# # Create table
c.execute('''CREATE TABLE curr_state (key string primary key, value text)''')
# # We can also close the connection if we are done with it.
# # Just be sure any changes have been committed or they will be lost.
conn.close()
