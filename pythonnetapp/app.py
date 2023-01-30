from flask import Flask, render_template, request, redirect, Blueprint
from evolved5g.sdk import QosAwareness,LocationSubscriber
from evolved5g.swagger_client import UsageThreshold
from evolved5g.swagger_client.rest import ApiException
from werkzeug.utils import secure_filename
import init_database
import db_controller
import emulator_utils

import requests
import json
import csv
import os
import sys
import datetime

ALLOWED_EXTENSIONS = set(['csv'])

## initialize variables
netapp_name=os.environ['NETAPP_NAME']
nef_ip=os.environ['NEF_IP']
app_ip=os.environ['NETAPP_IP']
nef_domain="@domain.com"

app = Blueprint("app", __name__, template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

# print("em "+emulator_utils.get_url_of_the_nef_emulator(), file=sys.stderr)
# print("os "+os.environ['NEF_IP'])
#qos_api_url = "http://"+nef_ip+":8888/nef/api/v1/3gpp-as-session-with-qos/v1/myNetapp/subscriptions"
#ue_url = "http://"+nef_ip+":8888/api/v1/UEs"
#cell_url = "http://"+nef_ip+":8888/api/v1/Cells"

## Flask app
app = Flask(__name__, template_folder='templates')


## Functions
#FILTER FOR FILENAME
# def allowed_file(filename):
#     return '.' in filename and \
#     filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#ALLINONE ADD
def SubcribeAndInsert(ip):
    print("Working with ip:",ip)

    ## subscribe to QoS and Location
    try:
        qos_id = Qos_CreateSubscription(ip)
    except:
        return render_template('error.html', error='There was a problem with qos!')

    try:
        event_id = Location_CreateSubscription(ip)
    except:
        return render_template('error.html', error='There was a problem with location!')


    try:
        ## save history event to database    
        action = "INSERT"
        details = "At {} IP : {} added in system".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip)
        db_controller.addHistoryEvent(ip,action,details)

        ## save ip to database
        db_controller.addIp(ip,qos_id,event_id)

        return True
    except:
        return render_template('error.html', error='There was a problem with DB!')


## Routes

#Default Route
@app.route('/')
def default():
    return redirect('/netapp')

#About
@app.route('/about')
def about():
    return render_template('about.html')

#Home
@app.route('/netapp', methods=['GET'])
def netapp():
    all_ips = db_controller.getIps()
    history = db_controller.getHistory()
    return render_template('index.html', ips=all_ips, history=history)

#Import csv
@app.route('/importcsv', methods=['POST'])
def importcsv():
    if request.method == 'POST':
        #folder: csv_input_file
        f=request.files['file']
        filename = secure_filename(f.filename)
        new_filename= f'{filename.split(".")[0]}_{str(datetime.datetime.now())}.csv'
        file_path = os.path.join("csv_input_files", new_filename)
        f.save(file_path)

        #CHECK IF THERE ARE IPS IN SYSTEM
        all_ips = db_controller.getIps()
        there_are_ips=bool(False)
        if all_ips:
            there_are_ips=bool(True)

        #OPEN CSV
        with open(file_path) as f:
            reader = csv.reader(f)
            #CHEK IPS IN CSV IF ALREADY EXIST IN SYSTEM
            for row in reader:
                check=bool(True)
                if there_are_ips:
                    for ip in all_ips:
                        print("Checking ip:",ip.ip,"with ip:",row[0],".")
                        if ip[1] == row[0]:
                            print("already exist!!!")
                            check=bool(False)
                            break
                if check:
                    #ADD IP
                    SubcribeAndInsert(row[0])
                    
    #IF CSV IS EMPTY OR CORRUPTED
    else:
        return default()
    return redirect('/netapp')
     
#Insert IP row
@app.route('/addip', methods=['POST'])
def addip():
    post_ip = request.form['ip']
    all_ips = db_controller.getIps()
    
    ## check if ip already exists
    for ip in all_ips:
        if ip[1] == post_ip:
            print ("\nIP already exists. Redirecting..")
            return redirect('/netapp')

    SubcribeAndInsert(post_ip)
    return redirect('/netapp')

#Delete IP row
@app.route('/delete/<int:id>')
def delete(id):
    ip = db_controller.searchById(id)
    # if ip[2] == "ALLOW":

    ## Unsubscribe
    try:
        print("Unsubscribing for ip: ",ip[1])
        Qos_Unsubscribe(ip)
        Location_Unsubscribe(ip)
    except:
        return render_template('error.html', error='There was a problem with delete!')

    ## Delete from database
    try:
        db_controller.deleteIp(ip[0])
    except:
        return render_template('error.html', error='There was a problem with DB!')
    
    ## Add to History
    try:
        action = "REMOVE"
        details = "At {} IP : {} removed from system".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip[1])
        db_controller.addHistoryEvent(ip[1],action,details)
        return redirect('/netapp')
    except:
        return render_template('error.html', error='There was a problem with history!')

## Update IP row
@app.route('/update/<int:id>', methods=['GET','POST'])
def update(id):
    ip = db_controller.searchById(id)

    current_id = ip[0]
    current_ip = ip[1]
    current_access = ip[2]
    current_date = ip[3]
    current_qos_id = ip[4]
    current_location_id = ip[5]

    if request.method == 'POST':
        ## same IP
        if current_ip == request.form['ip']:

            #IF ACCESS IS NOT THE SAME
            if current_access != request.form['access']:
                current_access = request.form['access']
                try:
                    if current_access == "ALLOW":
                        current_qos_id = Qos_CreateSubscription(current_ip)
                        current_location_id = Location_CreateSubscription(current_ip)
                    else:
                        Qos_Unsubscribe(ip)
                        Location_Unsubscribe(ip)
                        current_qos_id = "not_subscribed"
                        current_location_id = "not_subscribed"
                except:
                    return render_template('error.html', error='There was a problem with Update!')

        ## different IP
        else:
            current_ip = request.form['ip']
            try:
                Qos_Unsubscribe(ip)
                Location_Unsubscribe(ip)
                if request.form['access'] == "ALLOW":
                    current_qos_id = Qos_CreateSubscription(request.form['ip'])
                    current_location_id = Location_CreateSubscription(request.form['ip'])
                else:
                    current_qos_id = 'not_subscribed'
                    current_location_id = "not_subscribed"
            except:
                return render_template('error.html', error='There was a problem with Update!')
        
        ## update database
        try:
            db_controller.updateIp(current_id,current_ip,current_access,current_date,current_qos_id,current_location_id)
            return redirect('/netapp')
        except:
            return render_template('error.html', error='There was a problem with DB!')
    
    ## Get update html
    else:
        return render_template('update.html', ip=ip)

#SERACH BY ACCESS
@app.route('/netapp/SearchByAccess/<string:access>')
def SearchByAccess(access):
    delete_existing_qos_subscriptions()
    delete_existing_location_subscriptions()

    ips_all = db_controller.getIps()
    if access == "ALL":
        return render_template('index.html', ips=ips_all)
    else:
        all_ips = db_controller.searchByAccess(access)
        return render_template('index.html', ips=all_ips)


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
def Qos_CreateSubscription(ip):
    print("Trying New QoS subscription with ip: "+ ip)

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
                                        

    netapp_id = netapp_name
    notification_destination="http://172.17.0.1:5000/monitoring/callback"

    try:
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

        qos_id = subscription.link.split("/")[-1]
        print("--- Subscribed to Qos successfully with id " + qos_id + "----")
        try:
            action = "SUBSCRIPTION"
            details = "At {} IP : {} subscribed in qos notification".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip)
            db_controller.addHistoryEvent(ip,action,details)
        except:
            return render_template('error.html', error='There was a problem with history!')
        return qos_id

    except ApiException as ex:
        if ex.status == 409:
            print("There is already an active qos subscription for this ip " + equipment_network_identifier)
            return False, "There is already an active qos subscription" + equipment_network_identifier
        else:
            raise


#SUBSCRIBE EVENT IP
def Location_CreateSubscription(ip):
    print("Trying New location subscription with ip: "+ ip)
    
    location_subscriber = LocationSubscriber(
                            nef_url= emulator_utils.get_url_of_the_nef_emulator(),
                            nef_bearer_access_token= emulator_utils.get_token_for_nef_emulator().access_token,
                            folder_path_for_certificates_and_capif_api_key= emulator_utils.get_folder_path_for_certificated_and_capif_api_key(),
                            capif_host= emulator_utils.get_capif_host(),
                            capif_https_port= emulator_utils.get_capif_https_port() 
                        )

    netapp_id = netapp_name
    notification_destination="http://172.17.0.1:5000/monitoring/callback"

    #datetime monitor_expire_time: Identifies the absolute time at which the related monitoring event request is considered to expire
    expire_time = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat() + "Z"
    #str external_id: Globally unique identifier containing a Domain Identifier and a Local Identifier. <Local Identifier>@<Domain Identifier>
    external_id = ip.replace('.', '')+nef_domain

    try:
        event_subscription = location_subscriber.create_subscription(
            netapp_id=netapp_id,
            external_id=external_id,
            notification_destination=notification_destination,
            maximum_number_of_reports=1000,
            monitor_expire_time=expire_time
        )

        ## extract id
        event_id = event_subscription.link.split("/")[-1]
        print("--- Subscribed to Location successfully with id " + event_id + "----")

        try:
            action = "SUBSCRIPTION"
            details = "At {} IP : {} subscribed in event notification".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip)
            db_controller.addHistoryEvent(ip,action,details)
            return event_id
        except:
            return render_template('error.html', error='There was a problem with history!')

    except ApiException as ex:
        if ex.status == 409:
            print("There is already an active location subscription for UE with external id", external_id, '\n')
            return False, "There is already an active location subscription for UE with external id " + external_id
        else:
            raise




def delete_existing_qos_subscriptions():
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
            print("No active qos transcriptions found")
        else: #something else happened, re-throw the exception
            raise
    
def delete_existing_location_subscriptions():
    # How to get all subscriptions
    netapp_id = "myNetapp"
    location_subscriber = LocationSubscriber(
                            nef_url=emulator_utils.get_url_of_the_nef_emulator(),
                            nef_bearer_access_token= emulator_utils.get_token_for_nef_emulator().access_token,
                            folder_path_for_certificates_and_capif_api_key=emulator_utils.get_folder_path_for_certificated_and_capif_api_key(),
                            capif_host=emulator_utils.get_capif_host(),
                            capif_https_port=emulator_utils.get_capif_https_port()
                        )

    try:
        all_subscriptions = location_subscriber.get_all_subscriptions(netapp_id, 0, 100)
        # print(all_subscriptions)

        for subscription in all_subscriptions:
            id = subscription.link.split("/")[-1]
            print("Deleting location subscription with id: " + id)
            location_subscriber.delete_subscription(netapp_id, id)
    except ApiException as ex:
        if ex.status == 404:
            print("No active location transcriptions found")
        else: #something else happened, re-throw the exception
            raise



## Unsubscribe from Qos
def Qos_Unsubscribe(ip):
    netapp_id = netapp_name
    subscription_id = str(ip[4])

    print("QosUnsub id: ",subscription_id)

    if(subscription_id != "not_subscribed"):

        qos_awareness = QosAwareness(
                            nef_url=emulator_utils.get_url_of_the_nef_emulator(),
                            nef_bearer_access_token= emulator_utils.get_token_for_nef_emulator().access_token,
                            folder_path_for_certificates_and_capif_api_key=emulator_utils.get_folder_path_for_certificated_and_capif_api_key(),
                            capif_host=emulator_utils.get_capif_host(),
                            capif_https_port=emulator_utils.get_capif_https_port()
                        )

        try:
            qos_awareness.delete_subscription(netapp_id, subscription_id)

            action = "UNSUBSCRIPTION"
            details = "At {} IP : {} unsubscribed from qos notification".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip[1])
            db_controller.addHistoryEvent(ip[1],action,details)
        except:
            return render_template('error.html', error='There was a problem with unsubscribing from Qos!')

    else:
        return True
    
              
## Unsubscribe from Location Events
def Location_Unsubscribe(ip):
    netapp_id = netapp_name
    subscription_id = str(ip[5])

    print("LocationUnsub id: ",subscription_id)

    if(subscription_id != "not_subscribed"):

        location_subscriber = LocationSubscriber(
                                nef_url= emulator_utils.get_url_of_the_nef_emulator(),
                                nef_bearer_access_token= emulator_utils.get_token_for_nef_emulator().access_token,
                                folder_path_for_certificates_and_capif_api_key= emulator_utils.get_folder_path_for_certificated_and_capif_api_key(),
                                capif_host= emulator_utils.get_capif_host(),
                                capif_https_port= emulator_utils.get_capif_https_port() 
                            )

        try:
            location_subscriber.delete_subscription(netapp_id,subscription_id)

            action = "UNSUBSCRIPTION"
            details = "At {} IP : {} unsubscribed from event notification".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip[1])
            db_controller.addHistoryEvent(ip[1],action,details)
        except:
            return render_template('error.html', error='There was a problem with history!')

    else:
        return True



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
    details = "At {} IP : {} moved to a cell with qos: {}".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),qos_ip,qos)
    db_controller.addHistoryEvent(qos_ip,action,details)
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
    details = "At {} IP : {} BaseStation : {} moved to cell : {}".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),event_ip,enodeB_id,cell_id)
    db_controller.addHistoryEvent(event_ip,action,details)
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
    ## Initialize Postgres Database
    print("\nInitializing Database..")
    init_database.init_db()
    print("Netapp running..")
    
    # delete_existing_qos_subscriptions()
    # delete_existing_location_subscriptions()
    app.run(debug=True, host='0.0.0.0')