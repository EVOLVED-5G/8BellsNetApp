from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename
import init_database
import db_controller
import functions

import json, csv, os, datetime, paramiko

ALLOWED_EXTENSIONS = set(['csv'])
VAPP_SERVICE=True

## Initialize variables
netapp_name=os.environ['NETAPP_NAME']
nef_ip=os.environ['NEF_IP']
app_ip=os.environ['NETAPP_IP']
vapp_host=os.environ['VAPP_IP']
vapp_user=os.environ['VAPP_USER']
vapp_pass=os.environ['VAPP_PASS']
nef_domain="@domain.com"

app = Flask(__name__, template_folder='templates')

## Routes ##
# Default Route
@app.route('/')
def default():
    return redirect('/netapp')

## About
@app.route('/about')
def about():
    return render_template('about.html')

## Home
@app.route('/netapp', methods=['GET'])
def netapp():
    all_ips = db_controller.getIps()
    history = db_controller.getHistory()
    return render_template('index.html', ips=all_ips, history=history)

## Import csv
@app.route('/importcsv', methods=['POST'])
def importcsv():
    if request.method == 'POST':
        f=request.files['file']
        filename = secure_filename(f.filename)
        new_filename= f'{filename.split(".")[0]}_{str(datetime.datetime.now())}.csv'
        file_path = os.path.join("csv_input_files", new_filename)
        f.save(file_path)

        with open(file_path) as f:
            reader = csv.reader(f)
            for row in reader:

                ## fetch ips from table
                all_ips = db_controller.getIps()

                exist = False
                for ip in all_ips:
                    # print("Checking table ip:",ip[1],"with csv ip:",row[0])
                    if row[0] == ip[1]:
                        print("Ip "+ row[0] +" from the csv file has already been inserted!")
                        exist = True
                        break

                ## Add new ip
                if not exist:
                    functions.SubscribeAndInsert(row[0])
                    
    else:
        return default()
    return redirect('/netapp')
     
## Insert IP row
@app.route('/addip', methods=['POST'])
def addip():
    post_ip = request.form['ip']
    
    ## check if ip already exists
    if(db_controller.existsIp(post_ip)):
        print ("\nIP already exists. Redirecting..")
    else:
        functions.SubscribeAndInsert(post_ip)

    return redirect('/netapp')

## Delete IP row
@app.route('/delete/<int:id>')
def delete(id):
    ip = db_controller.searchById(id)

    ## Unsubscribe
    try:
        print("Unsubscribing for ip: ",ip[1])
        functions.Qos_Unsubscribe(ip)
        functions.Location_Unsubscribe(ip)
        ## VAPP
        delete_ip_flows(ip[1])
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
        details = "{} : IP {} removed from database".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip[1])
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

            ## if access is not the same
            if current_access != request.form['access']:
                current_access = request.form['access']
                try:
                    if current_access == "ALLOW":
                        current_qos_id = functions.Qos_CreateSubscription(current_ip)
                        current_location_id = functions.Location_CreateSubscription(current_ip)
                    else:
                        functions.Qos_Unsubscribe(ip)
                        functions.Location_Unsubscribe(ip)
                        current_qos_id = "not_subscribed"
                        current_location_id = "not_subscribed"
                        ## vapp
                        delete_ip_flows(current_ip)
                except:
                    return render_template('error.html', error='There was a problem with Update!')

        ## different IP
        else:
            current_ip = request.form['ip']
            try:
                functions.Qos_Unsubscribe(ip)
                functions.Location_Unsubscribe(ip)
                ## vapp
                delete_ip_flows(current_ip)

                if request.form['access'] == "ALLOW":
                    current_qos_id = functions.Qos_CreateSubscription(request.form['ip'])
                    current_location_id = functions.Location_CreateSubscription(request.form['ip'])
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

## Search by Access
@app.route('/netapp/SearchByAccess/<string:access>')
def SearchByAccess(access):
    
    all_ips = db_controller.getIps()
    history = db_controller.getHistory()

    if access == "ALL":
        return render_template('index.html', ips=all_ips, history=history)
    else:
        access_ips = db_controller.searchByAccess(access)
        return render_template('index.html', ips=access_ips, history=history)
    

@app.route('/netapp/deleteall', methods=['GET'])
def delete_all():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=vapp_host, username=vapp_user, password=vapp_pass)
    command = "ls -a"
    ssh.exec_command(command)

    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
    ssh_stdout.channel.set_combine_stderr(True)
    print("stdout ",ssh_stdout.readlines())

    functions.delete_all()
    return redirect('/netapp')


## Callback
@app.route('/monitoring/callback', methods=['POST'])
def notification_reporter():
    print("New event notification retrieved:")
    event_dict = json.loads(request.data)
    event_ip = event_dict["ipv4Addr"]

    if(db_controller.existsIp(event_ip)):

        if( next(iter(event_dict)) == "externalId"):

            cell_id=event_dict["locationInfo"]["cellId"]
            enodeB_id=event_dict["locationInfo"]["enodeBId"]

            action = "LOCATION NOTIFICATION"
            details = "At {} IP : {} BaseStation : {} moved to cell : {}".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),event_ip,enodeB_id,cell_id)
            db_controller.addHistoryEvent(event_ip,action,details)

        else:
            # print(event_dict)
            qos = event_dict["eventReports"][0]["event"]

            # SSH to vapp with event_ip
            if(qos == "QOS_NOT_GUARANTEED"):
                add_throttling_flows_vapp(event_ip)
                print(qos)
            else:
                # QOS_GUARANTEED
                add_allow_flows_vapp(event_ip)
                print(qos)

            action = qos
            details = "At {} IP : {} moved to a cell with qos: {}".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),event_ip,qos)
            db_controller.addHistoryEvent(event_ip,action,details)

    return '', 200

def add_allow_flows_vapp(event_ip):
    if(VAPP_SERVICE): 
        ssh = paramiko.SSHClient()

        # rsa_key = paramiko.RSAKey.from_private_key_file('/usr/src/app/vapp_onboarding/.ssh/id_rsa')
        # ssh.connect(hostname=vapp_host, username=vapp_user, pkey=rsa_key)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=vapp_host, username=vapp_user, password=vapp_pass)


        command = "sudo ovs-ofctl -O OpenFlow13 add-flow Firewall dl_type=0x0800,ip_src="+ event_ip +",priority=100,hard_timeout=360,actions=goto_table:100"
        ssh.exec_command(command)

        command = "sudo ovs-ofctl -O OpenFlow13 add-flow Firewall dl_type=0x0800,ip_dst="+ event_ip +",priority=101,hard_timeout=360,actions=goto_table:102"
        ssh.exec_command(command)

        # ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
        # ssh_stdout.channel.set_combine_stderr(True)
        # print("stdout ",ssh_stdout.readlines())
    

def add_throttling_flows_vapp(event_ip):
    if(VAPP_SERVICE):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=vapp_host, username=vapp_user, password=vapp_pass)

        command = "sudo ovs-ofctl -O OpenFlow13 add-flow Firewall dl_type=0x0800,ip_src="+ event_ip +",priority=100,hard_timeout=360,actions=goto_table:101"
        ssh.exec_command(command)

        command = "sudo ovs-ofctl -O OpenFlow13 add-flow Firewall dl_type=0x0800,ip_dst="+ event_ip +",priority=101,hard_timeout=360,actions=goto_table:103"
        ssh.exec_command(command)

def delete_ip_flows(event_ip):
    if(VAPP_SERVICE):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=vapp_host, username=vapp_user, password=vapp_pass)

        command = "sudo ovs-ofctl -O OpenFlow13 del-flows Firewall dl_type=0x0800,ip_src="+ event_ip
        print(command)
        ssh.exec_command(command)

        command = "sudo ovs-ofctl -O OpenFlow13 del-flows Firewall dl_type=0x0800,ip_dst="+ event_ip
        ssh.exec_command(command)


#event location 
# {
#     'externalId': '10003@domain.com',
#     'ipv4Addr': '10.0.0.3',
#     'subscription': 'http://10.10.10.35:8888/nef/api/v1/3gpp-monitoring-event/v1/myNetapp/subscriptions/63dbc86b91e36147e33dda94', 
#     'monitoringType': 'LOCATION_REPORTING', 
#     'locationInfo': {
#         'cellId': 'AAAAA1001',
#         'enodeBId': 'AAAAA1'
#     }
# }

#qos    
# {
#     'transaction': 'http://10.10.10.35:8888/nef/api/v1/3gpp-as-session-with-qos/v1/myNetapp/subscriptions/63dbc86b91e36147e33dda93', 
#     'ipv4Addr': '10.0.0.3', 
#     'eventReports': [{
#         'event': 'QOS_GUARANTEED', 
#         'accumulatedUsage': {
#             'duration': None, 
#             'totalVolume': None, 
#             'downlinkVolume': None, 
#             'uplinkVolume': None
#         }, 
#         'appliedQosRef': None, 
#         'qosMonReports': [{
#             'ulDelays': [0], 
#             'dlDelays': [0], 
#             'rtDelays': [0]
#         }]
#     }]
# }

if __name__ == '__main__':
    ## Initialize Postgres Database
    print("\n────────────────────────\n Initializing Database..")
    init_database.init_db()
    print("Netapp running..")

    app.run(debug=True, host='0.0.0.0')