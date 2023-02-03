import psycopg2,os

sql_add_ip = """INSERT INTO IP(ip,qos_id,event_id) VALUES(%s,%s,%s) RETURNING id;"""
sql_add_history = """INSERT INTO History(ip_name,action,details) VALUES(%s,%s,%s) RETURNING id;"""

dbname = os.environ['DB_NAME']
user = os.environ['DB_USERNAME']
host = os.environ['HOST']
password = os.environ['DB_PASS']
port = os.environ['DB_PORT']

#get connection with db
def connectDatabase():
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        host=host,
        password=password,
        port=port)
    return conn

## GET
#get all from ip table
def getHistory():
    conn = connectDatabase()
    cur = conn.cursor()
    cur.execute('SELECT * FROM HISTORY ORDER BY date_created DESC;')
    history = cur.fetchall()
    cur.close()
    conn.close()
    return history


#get all from ip table
def getIps():
    conn = connectDatabase()
    cur = conn.cursor()
    cur.execute('SELECT * FROM IP;')
    ips = cur.fetchall()
    cur.close()
    conn.close()
    return ips


#get ip info from ip
def searchById(id):
    conn = connectDatabase()
    cur = conn.cursor()
    cur.execute('SELECT * FROM IP WHERE id=%s;',[id])
    id = cur.fetchall()
    cur.close()
    conn.close()
    return id[0]

#get ip info from access
def searchByAccess(access):
    conn = connectDatabase()
    cur = conn.cursor()
    cur.execute('SELECT * FROM IP WHERE access=%s;',[access])
    ips = cur.fetchall()
    cur.close()
    conn.close()
    return ips

#add row in ip table
def addIp(ip,qos_id,event_id):
    conn = connectDatabase()
    cur = conn.cursor()
    id = cur.execute(sql_add_ip,(ip,qos_id,event_id))
    conn.commit()
    cur.close()
    conn.close()
    return id

#add row in history table
def addHistoryEvent(ip_name,action,details):
    conn = connectDatabase()
    cur = conn.cursor()
    id = cur.execute(sql_add_history,(ip_name,action,details))
    conn.commit()
    cur.close()
    conn.close()
    return id

#updates ip info
def updateIp(id,ip,access,date_created,qos_id,event_id):
    print(id,ip,access,date_created,qos_id,event_id)
    conn = connectDatabase()
    cur = conn.cursor()
    cur.execute('UPDATE IP SET ip = %s,access=%s,date_created=%s,\
        qos_id=%s,event_id=%s WHERE id = %s;',[ip,access,date_created,qos_id,event_id,id])
    conn.commit()
    cur.close()
    conn.close()
    return ip


#delete ip
def deleteIp(id):
    conn = connectDatabase()
    cur = conn.cursor()
    cur.execute('DELETE FROM IP WHERE id = %s;',[id])
    conn.commit()
    cur.close()
    conn.close()
    return

def deleteAllIps():
    conn = connectDatabase()
    cur = conn.cursor()
    cur.execute('DELETE FROM IP')
    conn.commit()
    cur.close()
    conn.close()
    return
