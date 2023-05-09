from evolved5g import swagger_client
from evolved5g.swagger_client import LoginApi, User
from evolved5g.swagger_client.models import Token
import os,requests

nef_user=os.environ['NEF_USER']
nef_password=os.environ['NEF_PASS']
nef_ip=os.environ['NEF_IP']
capifhost=os.environ['CAPIF_HOSTNAME']

def get_token_for_nef_emulator() -> Token:

    username = str(nef_user)
    password = str(nef_password)
    configuration = swagger_client.Configuration()

    # The host of the 5G API (emulator)
    configuration.host = get_url_of_the_nef_emulator()
    configuration.verify_ssl = False
    
    api_client = swagger_client.ApiClient(configuration=configuration)
    api_client.select_header_content_type(["application/x-www-form-urlencoded"])
    api = LoginApi(api_client)
    token = api.login_access_token_api_v1_login_access_token_post("", username, password, "", "", "")
    return token

def get_api_client_for_nef_emulator(token) -> swagger_client.ApiClient:
    configuration = swagger_client.Configuration()
    configuration.host = get_url_of_the_nef_emulator()
    configuration.access_token = token.access_token
    api_client = swagger_client.ApiClient(configuration=configuration)
    return api_client


def get_url_of_the_nef_emulator() -> str:
    return nef_ip

def get_folder_path_for_netapp_certificates_and_capif_api_key()->str:
    """
    This is the folder that was provided when you registered the NetApp to CAPIF.
    It contains the certificates and the api.key needed to communicate with the CAPIF server
    :return:
    """
    return "/usr/src/app/capif_onboarding"
    

def get_capif_host()->str:
    """
    When running CAPIF via docker (by running ./run.sh) you should have at your /etc/hosts the following record
    127.0.0.1       capifcore
    :return:
    """
    return capifhost

def get_capif_https_port()->int:
    """
    This is the default https port when running CAPIF via docker
    :return:
    """
    return 443