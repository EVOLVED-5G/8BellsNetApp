import db_controller

def init_db():
    connect_db= db_controller.connectDatabase()
    cur = connect_db.cursor()

    # Drop for changes
    cur.execute(""" DROP TABLE IF EXISTS IP """)
    cur.execute(""" DROP TABLE IF EXISTS History """)

    #TABLE IP
    sqlCreateTableIP = "create table if not exists IP (\
                        id serial primary key,\
                        ip varchar(200),\
                        access varchar(20) default 'ALLOW',\
                        date_created timestamp default now(),\
                        qos_id varchar(256) default 'not_subscribed',\
                        event_id varchar(256) default 'not_subscribed');"
    cur.execute(sqlCreateTableIP)

    #TABLE HISTORY
    sqlCreateTableHistory = "create table if not exists History (\
                            id serial primary key,\
                            ip_name varchar(256),\
                            date_created timestamp default now(),\
                            action varchar(256),\
                            details varchar(256));"
    cur.execute(sqlCreateTableHistory)

    ## Close the cursor and connection
    connect_db.commit()
    cur.close()
    connect_db.close()