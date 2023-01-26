import psycopg2

sql_add_ip = """INSERT INTO IP(ip,qos_id,event_id) VALUES(%s,%s,%s) RETURNING id;"""
sql_add_history="""INSERT INTO HISTORY(ip_name,action,details) VALUES(%s,%s,%s) RETURNING id;"""

#check connection between netapp and db
def connect():
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # read connection parameters
        params = get_db_connection()

        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params)
		
        # create a cursor
        cur = conn.cursor()

        
	# execute a statement
        print('PostgreSQL database version:')
        cur.execute('SELECT version()')

        # display the PostgreSQL database server version
        db_version = cur.fetchone()
        print(db_version)
       
	# close the communication with the PostgreSQL
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')

#get connection with db
def get_db_connection():
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        host="10.10.10.35",
        password="postgres",
        port=5432)
    return conn
#########TABLE HISTORY########
#get all from ip table
def get_all_history_from_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM HISTORY ORDER BY date_created DESC;')
    history = cur.fetchall()
    cur.close()
    conn.close()
    return history

#########TABLE IP#############
#get all from ip table
def get_all_from_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM IP;')
    ips = cur.fetchall()
    cur.close()
    conn.close()
    return ips

#get ip info from ip
def search_by_id(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM IP WHERE id=%s;',[id])
    id = cur.fetchall()
    cur.close()
    conn.close()
    return id[0]

#get ip info from access
def search_by_access(access):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM IP WHERE access=%s;',[access])
    ips = cur.fetchall()
    cur.close()
    conn.close()
    return ips

#delete ip
def delete_ip(ip_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM IP WHERE id = %s;',[ip_id])
    conn.commit()
    cur.close()
    conn.close()
    return

#add row in ip table
def add_IP(ip,qos_id,event_id):
    conn = get_db_connection()
    cur = conn.cursor()
    id = cur.execute(sql_add_ip,(ip,qos_id,event_id))
    conn.commit()
    cur.close()
    conn.close()
    return id

#add row in history table
def add_HISTORY(ip_name,action,details):
    conn = get_db_connection()
    cur = conn.cursor()
    id = cur.execute(sql_add_history,(ip_name,action,details))
    conn.commit()
    cur.close()
    conn.close()
    return id

#updates ip info
def update_ip(id,ip,access,date_created,qos_id,event_id):
    print(id,ip,access,date_created,qos_id,event_id)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE IP SET ip = %s,access=%s,date_created=%s,\
        qos_id=%s,event_id=%s WHERE id = %s;',[ip,access,date_created,qos_id,event_id,id])
    conn.commit()
    cur.close()
    conn.close()
    return

#main
if __name__ == '__main__':
    connect()