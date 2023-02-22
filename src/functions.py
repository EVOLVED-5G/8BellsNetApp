from flask import render_template
from evolved5g.sdk import QosAwareness,LocationSubscriber
from evolved5g.swagger_client import UsageThreshold
from evolved5g.swagger_client.rest import ApiException

import db_controller
import emulator_utils
import datetime, os

netapp_name=os.environ['NETAPP_NAME']
nef_ip=os.environ['NEF_IP']
app_ip=os.environ['NETAPP_IP']
callback_address=os.environ['CALLBACK_ADR']
nef_domain="@domain.com"


## Subscribe and Insert to database
def SubscribeAndInsert(ip):
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
        details = "{} : IP {} inserted in database".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip)
        db_controller.addHistoryEvent(ip,action,details)

        ## save ip to database
        db_controller.addIp(ip,qos_id,event_id)

        return True
    except:
        return render_template('error.html', error='There was a problem with DB!')

## Subscribe QoS
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
    notification_destination = callback_address

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
            reporting_mode=QosAwareness.EventTriggeredReportingConfiguration(wait_time_in_seconds=5)
            # reporting_mode=QosAwareness.PeriodicReportConfiguration(repetition_period_in_seconds=10)
        )

        qos_id = subscription.link.split("/")[-1]
        print("--- Subscribed to Qos successfully with id " + qos_id + "----")
        try:
            action = "SUBSCRIPTION"
            details = "{} : IP {} subscribed in QoS notification".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip)
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


## Subscribe Location event
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
    notification_destination = callback_address

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
            details = "{} : IP {} subscribed in Location notification".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip)
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
            details = "{} : IP {} unsubscribed from QoS notification".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip[1])
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
            details = "{} : IP {} unsubscribed from Location notification".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),ip[1])
            db_controller.addHistoryEvent(ip[1],action,details)
        except:
            return render_template('error.html', error='There was a problem with history!')

    else:
        return True



def delete_existing_qos_subscriptions():
    # How to get all subscriptions
    netapp_id = netapp_name
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
    netapp_id = netapp_name
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


def delete_all():
    delete_existing_qos_subscriptions()
    delete_existing_location_subscriptions()
    db_controller.deleteAllIps()