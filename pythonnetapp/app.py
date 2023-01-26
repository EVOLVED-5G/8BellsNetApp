from flask import Flask, render_template, request, redirect,  Blueprint
from evolved5g.sdk import QosAwareness,LocationSubscriber
from evolved5g.swagger_client import UsageThreshold
from evolved5g.swagger_client.rest import ApiException
from werkzeug.utils import secure_filename
from db_controller import *

import emulator_utils
import requests
import json
import csv
import os
import sys
import time
from datetime import datetime

ALLOWED_EXTENSIONS = set(['csv'])

#variables
app_name=os.environ['NETAPP_NAME']
nef_ip=os.environ['NEF_IP']
app_ip=os.environ['NETAPP_IP']

#####################
#NEF CONNECTION URLS#
#####################
app = Blueprint("app", __name__, template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
login_url = nef_ip+"api/v1/login/access-token"

# print("em "+emulator_utils.get_url_of_the_nef_emulator(), file=sys.stderr)
# print("os "+os.environ['NEF_IP'])

#qos_api_url = "http://"+nef_ip+":8888/nef/api/v1/3gpp-as-session-with-qos/v1/myNetapp/subscriptions"
#ue_url = "http://"+nef_ip+":8888/api/v1/UEs"
#cell_url = "http://"+nef_ip+":8888/api/v1/Cells"
#NEF DOMAIN NAME
nef_domain="@domain.com"
#######################
##FLASK CONFIGURATION##
#######################
app = Flask(__name__, template_folder='templates')
###############################
##########POSTGRES_DB##########
###############################

connect_db= get_db_connection()
cur = connect_db.cursor()

#TABLE IP
sqlCreateTableIP = "create table if not exists IP (\
id serial primary key,\
ip varchar(200),\
access varchar(256) default 'ALLOW',\
date_created timestamp default now(),\
qos_id varchar(256) default 'not_subscribed',\
event_id varchar(256) default 'not_subscribed');"
cur.execute(sqlCreateTableIP)

#TABLE HISTORY
sqlCreateTableHISTORY = "create table if not exists HISTORY (\
id serial primary key,\
ip_name varchar(256),\
date_created timestamp default now(),\
action varchar(256),\
details varchar(256));"
cur.execute(sqlCreateTableHISTORY)
connect_db.commit()
cur.close()
connect_db.close()

###############
###FUNCTIONS###
###############

#FILTER FOR FILENAME
def allowed_file(filename):
    return '.' in filename and \
    filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#ALLINONE ADD
def thebigadd(ip):
    print("Big Adding ip:",ip,file=sys.stderr)
    #SUBSCRIPTION qos
    try:
        qos_id = SubscriptionMaker(ip)
    except:
        return render_template('error.html', error='There was a problem with NEF:qos!')
    #SUBSCRIPTION event
    try:
        event_id = SubscriptionEventMaker(ip)
    except:
        return render_template('error.html', error='There was a problem with NEF:event!')
    #SAVE
    try:
        add_IP(ip,qos_id,event_id)
        action = "INSERT"
        details = "At {} IP : {} added in system".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip)
        add_HISTORY(ip,action,details)
        return
    except:
        return render_template('error.html', error='There was a problem with DB!')

############################################
##############ROUTES########################
############################################

#DEFAULT ROUTE
@app.route('/')
def default():
    return redirect('/netapp')

#ABOUT
@app.route('/about')
def about():
    return render_template('about.html')

#NETAPP
@app.route('/netapp', methods=['GET'])
def netapp():
    ips=get_all_from_db()
    history=get_all_history_from_db()
    return render_template('index.html', ips=ips,history=history)

#IMPORT FROM CSV
@app.route('/importcsv', methods=['POST'])
def importcsv():
    if request.method=='POST':
        #SAVE CSV FILE IN FOLDER: csv_input_file
        f=request.files['file']
        filename = secure_filename(f.filename)
        new_filename= f'{filename.split(".")[0]}_{str(datetime.now())}.csv'
        file_path = os.path.join("csv_input_files", new_filename)
        f.save(file_path)
        #CHECK IF THERE ARE IPS IN SYSTEM
        ips = get_all_from_db()
        there_are_ips=bool(False)
        if ips:
            there_are_ips=bool(True)
        #OPEN CSV
        with open(file_path) as f:
            reader = csv.reader(f)
            #CHEK IPS IN CSV IF ALREADY EXIST IN SYSTEM
            for row in reader:
                check=bool(True)
                if there_are_ips:
                    for ip in ips:
                        print("Checking ip:",ip.ip,"with ip:",row[0],".")
                        if ip[1] == row[0]:
                            print("already exist!!!")
                            check=bool(False)
                            break
                if check:
                    #ADD IP
                    thebigadd(row[0])
                    
    #IF CSV IS EMPTY OR CORRUPTED
    else:
        return default()
    return redirect('/netapp')
     
#ADD IP
@app.route('/addip', methods=['POST'])
def addip():
    post_ip = request.form['ip']
    ips = get_all_from_db()
    #CHECK IF IP EXISTS
    for ip in ips:
        if ip[1] == post_ip:
            print ("redirecting..", file=sys.stderr)
            return redirect('/netapp')
    thebigadd(post_ip)
    return redirect('/netapp')

#DELETE IP
@app.route('/delete/<int:id>')
def delete(id):
    ip=search_by_id(id)
    if ip[2] == "ALLOW":
        #UNSUBSCRIBE
        try:
            print("Unsubscrition for ip",ip[1])
            UnSubscriptionMaker(ip)
            UnSubscriptionEventMaker(ip)
            print("all ok")
        except:
            return render_template('error.html', error='There was a problem with NEF!')
    #DELETE
    try:
        delete_ip(ip[0])
    except:
        return render_template('error.html', error='There was a problem with DB!')
    #HISTORY
    try:
        action = "REMOVE"
        details = "At {} IP : {} removed from system".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip[1])
        add_HISTORY(ip[1],action,details)
        return redirect('/netapp')
    except:
        return render_template('error.html', error='There was a problem with history!')

#UPDATE IP
@app.route('/update/<int:id>', methods=['GET','POST'])
def update(id):
    ip = search_by_id(id)
    #print(ip)
    up_ip_id=ip[0]
    up_ip_ip=ip[1]
    up_ip_access=ip[2]
    up_ip_date=ip[3]
    up_ip_qos_id=ip[4]
    up_ip_event_id=ip[5]
    if request.method == 'POST':
        #IF IP IS THE SAME
        if ip[1] == request.form['ip']:
            #IF ACCESS IS NOT THE SAME
            if ip[2] != request.form['access']:
                up_ip_access = request.form['access']
                try:
                    if up_ip_access == "ALLOW":
                        up_ip_qos_id = SubscriptionMaker(ip[1])
                        up_ip_event_id = SubscriptionEventMaker(ip[1])
                    else:
                        UnSubscriptionMaker(ip)
                        UnSubscriptionEventMaker(ip)
                        up_ip_qos_id = "not_subscribed"
                        up_ip_event_id = "not_subscribed"
                except:
                    return render_template('error.html', error='There was a problem with NEF!')
        #IF IP IS NOT THE SAME
        else:
            try:
                UnSubscriptionMaker(ip)
                UnSubscriptionEventMaker(ip)
                if request.form['access'] == "ALLOW":
                    up_ip_qos_id = SubscriptionMaker(request.form['ip'])
                    up_ip_event_id = SubscriptionEventMaker(request.form['ip'])
                else:
                    up_ip_qos_id = 'not_subscribed'
            except:
                return render_template('error.html', error='There was a problem with NEF!')
            up_ip_ip = request.form['ip']
        #UPDATE
        try:
            update_ip(up_ip_id,up_ip_ip,up_ip_access,up_ip_date,up_ip_qos_id,up_ip_event_id)
            return redirect('/netapp')
        except:
            return render_template('error.html', error='There was a problem with DB!')
    else:
        return render_template('update.html', ip=ip)

#SERACH BY ACCESS
@app.route('/netapp/SearchByAccess/<string:access>')
def SearchByAccess(access):
    ips_all = get_all_from_db()
    if access == "ALL":
        return render_template('index.html', ips=ips_all)
    else:
        ips = search_by_access(access)
        return render_template('index.html', ips=ips)

################ NEF GETS AND POSTS     ##############

#LOGIN TO NEF
@app.route("/unregistered_traffic", methods=["POST", "GET"])
def login():
    body = {
        "username": "admin@my-email.com",
        "password": "pass"
    }

    try:
        ## try to login 
        nefResponse = requests.post(nef_ip+'/api/v1/login/access-token', data=body)
        print("Successfull login at NEF with response:",nefResponse,file=sys.stderr)

        ## extract token
        # token = nefResponse.json()
        # print(token,file=sys.stderr)

        ## test token
        # nefHeaders = {"Authorization": token['token_type'] + ' ' + token['access_token']}
        # nefResponse = requests.post(nef_ip+'/api/v1/login/test-token', headers=nefHeaders)
        # print(nefResponse.json(),file=sys.stderr)
    except Exception as e:
        print("Didnt manage to login",file=sys.stderr)
        raise e


#SUBSCRIBE QOS IP
def SubscriptionMaker(ip):
    print("new qos subscription:"+ ip)

    netapp_id = app_name
  
    qos_awareness = QosAwareness(
                        nef_url=emulator_utils.get_url_of_the_nef_emulator(),
                        nef_bearer_access_token= emulator_utils.get_token_for_nef_emulator().access_token,
                        folder_path_for_certificates_and_capif_api_key=emulator_utils.get_folder_path_for_certificated_and_capif_api_key(),
                        capif_host=emulator_utils.get_capif_host(),
                        capif_https_port=emulator_utils.get_capif_https_port()
                    )

    equipment_network_identifier = ip
    network_identifier = QosAwareness.NetworkIdentifier.IP_V4_ADDRESS
    conversational_voice = QosAwareness.GBRQosReference.CONVERSATIONAL_VOICE
    # In this scenario we monitor UPLINK
    uplink = QosAwareness.QosMonitoringParameter.UPLINK
    # Minimum delay of data package during uplink, in milliseconds
    uplink_threshold = 20
    gigabyte = 1024 * 1024 * 1024
    # Up to 10 gigabytes 5 GB downlink, 5gb uplink

    usage_threshold = UsageThreshold(
                        duration= None, # not supported
                        total_volume=10 * gigabyte,  # 10 Gigabytes of total volume
                        downlink_volume=5 * gigabyte,  # 5 Gigabytes for downlink
                        uplink_volume=5 * gigabyte  # 5 Gigabytes for uplink
                    )
                                        
    print("after usage and qos",file=sys.stderr)

    notification_destination="http://172.17.0.1:5000/monitoring/callback"

    # try:
    subscription = qos_awareness.create_guaranteed_bit_rate_subscription(
        netapp_id=netapp_id,
        equipment_network_identifier=equipment_network_identifier,
        network_identifier=network_identifier,
        notification_destination=notification_destination,
        gbr_qos_reference=conversational_voice,
        usage_threshold=usage_threshold,
        qos_monitoring_parameter=uplink,
        threshold=uplink_threshold,
        reporting_mode= QosAwareness.EventTriggeredReportingConfiguration(wait_time_in_seconds=10)
    )

    # print(subscription,file=sys.stderr)

    # Request information about a subscription
    qos_id = subscription.link.split("/")[-1]
    subscription_info = qos_awareness.get_subscription(netapp_id, qos_id)
    print("--- Subscribed with Qos successfully with id" + qos_id + "----")
    # print(subscription_info,file=sys.stderr)
    try:
        action = "SUBSCRIPTION"
        details = "At {} IP : {} subscribed in qos notification".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip)
        add_HISTORY(ip,action,details)
    except:
        return render_template('error.html', error='There was a problem with history!')
    return qos_id



def read_and_delete_all_existing_subscriptions():
    # How to get all subscriptions
    netapp_id = "myNetapp"
    qos_awareness = QosAwareness(
                        nef_url=emulator_utils.get_url_of_the_nef_emulator(),
                        nef_bearer_access_token= emulator_utils.get_token_for_nef_emulator().access_token,
                        folder_path_for_certificates_and_capif_api_key=emulator_utils.get_folder_path_for_certificated_and_capif_api_key(),
                        capif_host=emulator_utils.get_capif_host(),
                        capif_https_port=emulator_utils.get_capif_https_port()
                    )

    try:
        all_subscriptions = qos_awareness.get_all_subscriptions(netapp_id)
        # print(all_subscriptions)

        for subscription in all_subscriptions:
            subscription_id = subscription.link.split("/")[-1]
            print("Deleting qos subscription with id: " + subscription_id)
            qos_awareness.delete_subscription(netapp_id, subscription_id)
    except ApiException as ex:
        if ex.status == 404:
            print("No active transcriptions found")
        else: #something else happened, re-throw the exception
            raise



#UNSUBSCRIBE QOS IP
def UnSubscriptionMaker(ip):
    #it will send a UN-subscription in nef for the ip
    #print('unsubscribed:')
    #print(ip[1])
    #print(ip[4])
    netapp_id = app_name
    subscription_id = ip[4]
    #host = emulator_utils.get_host_of_the_nef_emulator()
    #token = emulator_utils.get_token()
    token=login()
    qos_awareness = QosAwareness(
                        nef_url=emulator_utils.get_url_of_the_nef_emulator(),
                        nef_bearer_access_token= emulator_utils.get_token_for_nef_emulator().access_token,
                        folder_path_for_certificates_and_capif_api_key=emulator_utils.get_folder_path_for_certificated_and_capif_api_key(),
                        capif_host=emulator_utils.get_capif_host(),
                        capif_https_port=emulator_utils.get_capif_https_port()
                    )

    unsubscription = qos_awareness.delete_subscription(netapp_id,subscription_id)
    try:
        #print("teeeeeeest")
        action = "UNSUBSCRIPTION"
        details = "At {} IP : {} unsubscribed from qos notification".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip[1])
        add_HISTORY(ip[1],action,details)
    except:
        return render_template('error.html', error='There was a problem with history!')
    
#SUBSCRIBE EVENT IP
def SubscriptionEventMaker(ip):
    print("new location subscription:"+ ip)
    
    location_subscriber = LocationSubscriber(
                            nef_url= emulator_utils.get_url_of_the_nef_emulator(),
                            nef_bearer_access_token= emulator_utils.get_token_for_nef_emulator().access_token,
                            folder_path_for_certificates_and_capif_api_key= emulator_utils.get_folder_path_for_certificated_and_capif_api_key(),
                            capif_host= emulator_utils.get_capif_host(),
                            capif_https_port= emulator_utils.get_capif_https_port() 
                        )
    #str external_id: Globally unique identifier containing a Domain Identifier and a Local Identifier. <Local Identifier>@<Domain Identifier>
    external_id = ip.replace('.', '')+nef_domain

    print("domain: "+external_id)

    #str netapp_id: string (The ID of the Netapp that creates a subscription)
    netapp_id = app_name
    notification_destination="http://172.17.0.1:5000/monitoring/callback"

    #datetime monitor_expire_time: Identifies the absolute time at which the related monitoring event request is considered to expire
    expire_time = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat() + "Z"

    try:
        event_subscription = location_subscriber.create_subscription(
            netapp_id=netapp_id,
            external_id=external_id,
            notification_destination=notification_destination,
            maximum_number_of_reports=1000,
            monitor_expire_time=expire_time
        )
        print("Try: ta katafera")
        # Request information about a subscription
        event_id = event_subscription.link.split("/")[-1]
        subscription_info = location_subscriber.get_subscription(netapp_id, event_id)

        print("--- RETRIEVING INFORMATION ABOUT SUBSCRIPTION " + event_id + "----")

          # How to get all subscriptions
        all_subscriptions = location_subscriber.get_all_subscriptions(netapp_id, 0, 100)
        print(all_subscriptions)
        #print(subscription_info)
        try:
            action = "SUBSCRIPTION"
            details = "At {} IP : {} subscribed in event notification".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip)
            add_HISTORY(ip,action,details)
        except:
            return render_template('error.html', error='There was a problem with history!')
        return event_id

    except ApiException as ex:
        if ex.status == 409:
            print("\nThere is already an active subscription for UE with external id", external_id, '\n')
            return False, "There is already an active subscription for UE with external id " + external_id
        else:
            raise

    
              
#UNSUBSCRIBE EVENT IP             
def UnSubscriptionEventMaker(ip):
    netapp_id = app_name
    subscription_id = ip[5]
    token=login()
    location_subscriber = LocationSubscriber(
                                            nef_url= emulator_utils.get_url_of_the_nef_emulator(),
                                            nef_bearer_access_token= emulator_utils.get_token_for_nef_emulator().access_token,
                                            folder_path_for_certificates_and_capif_api_key= emulator_utils.get_folder_path_for_certificated_and_capif_api_key(),
                                            capif_host= emulator_utils.get_capif_host(),
                                            capif_https_port= emulator_utils.get_capif_https_port() 
                                            )
    unsubscription = location_subscriber.delete_subscription(netapp_id,subscription_id)
    try:
        action = "UNSUBSCRIPTION"
        details = "At {} IP : {} unsubscribed from event notification".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip[1])
        add_HISTORY(ip[1],action,details)
    except:
        return render_template('error.html', error='There was a problem with history!')

#QOS NOTIFICATION
@app.route('/qosmonitoring/callback', methods=['POST'])
def location_qos_reporter():
    print("New qos notification retrieved:")
    qos_dict=json.loads(request.data)
    qos_ip=qos_dict["ipv4Addr"]
    #qos_id=qos_dict["transaction"].split("/")[-1]
    qos=qos_dict["eventReports"][0]["event"]
    #print("qos id:",qos_id)
    #print("qos :",qos)
    action = "QOS NOTIFICATION"
    details = "At {} IP : {} moved to a cell with qos: {}".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),qos_ip,qos)
    add_HISTORY(qos_ip,action,details)
    return "status 200"

#EVENT NOTIFICATION
@app.route('/eventmonitoring/callback', methods=['POST'])
def location_event_reporter():
    print("New event notification retrieved:")
    event_dict=json.loads(request.data)
    event_ip=event_dict["ipv4Addr"]
    #event_id=event_dict["subscription"].split("/")[-1]
    #loc_info=event_dict["locationInfo"]
    cell_id=event_dict["locationInfo"]["cellId"]
    enodeB_id=event_dict["locationInfo"]["enodeBId"]
    #print("event id:",event_id)
    #print("event report:",enodeB_id+"  "+cell_id)
    action = "EVENT NOTIFICATION"
    details = "At {} IP : {} BaseStation : {} moved to cell : {}".format(datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),event_ip,enodeB_id,cell_id)
    add_HISTORY(event_ip,action,details)
    return "status 200"

#event  {
# 'externalId': '10002@domain.com', 
# 'ipv4Addr': '10.0.0.2', 
# 'subscription': 'http://172.20.23.53:8888/nef/api/v1/3gpp-monitoring-event/v1/NetApp_app/subscriptions/6349313c64269f9928f70e98', 
# 'monitoringType': 'LOCATION_REPORTING', 
# 'locationInfo': {'cellId': 'AAAAA1002', 'enodeBId': 'AAAAA1'}}

#qos    {
# 'transaction': 'http://172.20.23.53:8888/nef/api/v1/3gpp-as-session-with-qos/v1/NetApp_app/subscriptions/6349313c64269f9928f70e95', 
# 'ipv4Addr': '10.0.0.2', 
# 'eventReports': [{
#       'event': 'QOS_NOT_GUARANTEED', 
#       'accumulatedUsage': {
#           'duration': None, 
#           'totalVolume': None, 
#           'downlinkVolume': None, 
#           'uplinkVolume': None}, 
#       'appliedQosRef': None, 
#       'qosMonReports': [{'ulDelays': [0], 'dlDelays': [0], 'rtDelays': [0]}]
#       }]
# }

if __name__ == '__main__':
    print("\nNetapp running..")
    read_and_delete_all_existing_subscriptions()
    app.run(debug=True, host='0.0.0.0')