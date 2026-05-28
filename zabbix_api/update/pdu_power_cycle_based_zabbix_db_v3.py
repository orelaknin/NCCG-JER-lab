import subprocess
import socket
import argparse
import time
import pexpect
import asyncio
import logging
import sys
import os
import re
from zabbix_api import ZabbixAPI
import time
from requests.exceptions import Timeout, RequestException


# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "update"
password = "$giga"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

sys.stderr = open(os.devnull, 'w')

haifa_script_path = "/home/laduser/haifa_script_altuscn/haifa_altuscn.py"
password_haifa = "$giga"

final_break_flag = None


def get_pdu_model_from_zabbix(zapi, ip_address):
    try:
        hosts = zapi.host.get({
            "output": ["hostid", "name"],
            "selectInterfaces": ["ip"],
            "selectItems": ["itemid", "name", "key_", "lastvalue"],
            "filter": {
                "ip": ip_address
            }
        })
        
        if not hosts:
            print(f"No host found with IP address: {ip_address}")
            return None
        
        host = hosts[0]
        model = None
        
        for item in host['items']:
            if item['name'] == "Generic SNMP: System description":
                model = item['lastvalue']
                break
        
        if model:
            return model
        else:
            return f"No model information found for IP {ip_address}"
        
    except Timeout:
        print(f"Timeout occurred. Retrying in 5 seconds...")
        time.sleep(5)
        return None
    except RequestException as e:
        print(f"Error occurred: {e}. Retrying in 5 seconds...")
        time.sleep(5)
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def snmp_get(community, target, oid, change_snmp_ver=False):
    try:
        if change_snmp_ver == False:
            result = subprocess.check_output(
                ['snmpget', '-v2c', '-c', community, target, oid],
                timeout=7,
                stderr=subprocess.STDOUT
            ).decode('utf-8')
            return result
        elif change_snmp_ver == True:
            result = subprocess.check_output(
                ['snmpget', '-v1', '-c', community, target, oid],
                stderr=subprocess.STDOUT
            ).decode('utf-8')
            return result.split('=')[1].strip()
        
            
    except subprocess.CalledProcessError as e:
        return "net_rec_pdu"


def snmp_set(community, target, oid, value, change_snmp_ver=False):
    try:
        if change_snmp_ver == False:
            result = subprocess.check_output(
                ['snmpset', '-v2c', '-c', community, target, oid, 'i', str(value)],
                stderr=subprocess.STDOUT
            ).decode('utf-8')
            return result
        elif change_snmp_ver == True:
            result = subprocess.check_output(
                ['snmpset', '-v1', '-c', community, target, oid, 'i', str(value)],
                stderr=subprocess.STDOUT
            ).decode('utf-8')
            return result
    except subprocess.CalledProcessError as e:
        print(f"Error executing snmpset: {e.output.decode('utf-8')}")


def create_parser():

    # Function to validate the IP address
    def valid_ip(ip_str):
        pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
        
        if "lab" in ip_str or "ttm" in ip_str:
            return str(ip_str)
        
        if not pattern.match(ip_str):
            print(f"Invalid IP address or Wrong TTM name {ip_str}")
            sys.exit(1)
        # Check that each part of the IP address is within the range 0-255
        parts = ip_str.split('.')
        for part in parts:
            if int(part) < 0 or int(part) > 255:
                print(f"IP address part out of range: {part}")
                sys.exit(1)
        return str(ip_str)

    # Function to validate outlet number (1-16 or 32 for ttm)
    def valid_outlet(outlet_str):
        outlet = int(outlet_str)
        if outlet < 1 or outlet > 32:
            print(f"Outlet must be a number between 1 and 16: {outlet_str}")
            sys.exit(1)
        return str(outlet)

    # Function to validate action number (0-2)
    def valid_action(action_str):
        action = int(action_str)
        if action < 0 or action > 2:
            print(f"Action must be a number between 0 and 2: {action_str}")
            sys.exit(1)
        return str(action)

    parser = argparse.ArgumentParser("pdu_power_cycle_ha.py")

    parser.add_argument("-i", "--ip", type=valid_ip, help="ip address", required=True)
    parser.add_argument("-o", "--outlet", type=valid_outlet, help="optional flag for remote json file", required=True)
    parser.add_argument("-a", "--action", type=valid_action, help="action to perform (on, off, cycle)", required=True)

    return parser


def check_ip_if_haifa(ip):
    
    if "143.185" in ip or "10.189" in ip:
        return "Ha"
    else:
        return None



async def check_if_altuscn(ip, outlet, action):
    
    pdu_name = ""
    
    result = check_ip_if_haifa(ip)

    #this step uses only ip, other arguments hardcoded for correct pattern of haifa's script
    args_for_haifa = [f"-i{ip}", f"-o{outlet}", f"-a{action}"]


    if result == "Ha":
        
        remote_command = f'python3 {haifa_script_path} ' + ' '.join(args_for_haifa)

        ssh_command = f"sshpass -p '{password_haifa}' ssh -o StrictHostKeyChecking=no laduser@143.185.151.119 '{remote_command}'"

        haifa_result = subprocess.run(ssh_command, shell=True, capture_output=True, text=True)
        
        if "Altuscn" in haifa_result.stdout:
            pdu_name = "Altuscn"
            print("Success")
            sys.exit(0)
            return pdu_name
        else: 
            return None
    
    else:

        child = pexpect.spawn(f"telnet {ip}")
        
        index = child.expect(["PN9108", pexpect.EOF, pexpect.TIMEOUT], timeout=1)    

        if index == 0:
            pdu_name = "Altuscn"
            return pdu_name
        pdu_name = "dbg_alt"
        return pdu_name
    

async def check_if_raritan(ip):

    # SNMP community and target settings
    read_community = 'NCCGRR'
    target = ip  # Replace with your PDU's IP address


    # OID for the PDU outlet status
    oid = '1.3.6.1.4.1.13742.6.3.2.1.1.2.1'
    

    # Get the current status
    pdu_manufacturer = snmp_get(read_community, target, oid)
    
    if "Raritan" in pdu_manufacturer:
        return "Raritan"
    
    return "not_rec_pdu"


async def check_if_aten(ip):
    
    # SNMP community and target settings
    read_community = 'NCCGRR'
    target = ip  # Replace with your PDU's IP address
    generic_model = ["PE6208AV","PE8216G","PE6108G", "PE6216G"]
    #"pe6108", "pe6216", "pe6208"

    # OID for the PDU outlet status
    oid = '1.3.6.1.4.1.21317.1.3.2.2.2.1.1.0'
    

    # Get the current status
    status = snmp_get(read_community, target, oid)
    

    for model in generic_model:
        if model in status:
            return "Aten"
        
    return "not_rec_pdu"
        

async def check_if_eaton(ip):
    
    # SNMP community and target settings
    read_community = 'NCCGRR'
    target = ip  # Replace with your PDU's IP address
    
    change_snmp_ver = True
    
    # OID for the PDU outlet status
    oid = '1.3.6.1.4.1.534.6.6.7.1.2.1.2.0'
    

    # Get the current status
    
    #status_other_pdu = snmp_get(read_community, target, oid)
    status_eaton = snmp_get(read_community, target, oid, change_snmp_ver)


    

    if "EPDU" in status_eaton:
        return "Eaton"
    else:
        return "not_rec_pdu"
    

def check_ttm_device(ip):

    gpio_power_script_name = "power.py"

    command = f"sshpass -p root00 ssh -o StrictHostKeyChecking=no root@{ip} 'find /root -name {gpio_power_script_name}'"
    
    
    try: 
        check_ttm_name = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE)
        
        if "power.py" in str(check_ttm_name.stdout):
            return "ttm_gpio"
        return "ttm_simple"

    except subprocess.CalledProcessError as e:
        print(f"Ttm fail error: {e}")

async def first_to_complete_rec(*tasks):

    tasks = [asyncio.create_task(task) for task in tasks]

    done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
    
    result = []

    for task in done:
        if task is not None:
            result.append(task.result())


    for task in pending:
        task.cancel()

    return result


def run_on_altuscn_pdu(ip, port, action):

    telnet_user = "root"
    telnet_password = "root00"

    child = pexpect.spawn(f"telnet {ip}")

    child.expect("Login")
    child.sendline(f"{telnet_user}\r")
    child.expect("Password")
    child.sendline(f"{telnet_password}\r")
    child.expect("==>")

    child.sendline("2\r")
    child.expect("==>")

    child.sendline("1\r")
    child.expect("==>")

    child.sendline("2\r")
    child.expect("==>")

    child.sendline(f"{port}\r")
    child.expect("==>")

    child.sendline(f"{action}\r")
    child.expect("==>")

    child.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=1)

    print("Success")

    return None


def run_on_aten_pdu(ip, port, action):

    # SNMP community and target settings
    write_community = 'NCCGWW'
    target = ip  # Replace with your PDU's IP address
    outlet = int(port)
    
    # OID for the PDU outlet status
    
    if outlet < 9:
        oid = f"1.3.6.1.4.1.21317.1.3.2.2.2.2.{outlet + 1}.0"
    else: 
        oid =  f"1.3.6.1.4.1.21317.1.3.2.2.2.2.{outlet + 2}.0"      

    # Get the current status
    #outlet_status = snmp_get(write_community, target, oid)


    if action == "0":
        new_status = "1"
    elif action == "1":
        new_status = "2"
    elif action == "2":
        new_status = "4"
    
    result = snmp_set(write_community, target, oid, new_status)
    
    if "INTEGER" in result:
        print("Success")
    else:
        print("Error")
    
    # Verify the change
    #outlet_status = snmp_get(write_community, target, oid)

    

    


def run_on_raritan_pdu(ip, port, action):

    # SNMP community and target settings
    write_community = 'NCCGWW'
    target = ip  # Replace with your PDU's IP address

    # OID for the PDU outlet status
    oid = f"1.3.6.1.4.1.13742.6.4.1.2.1.2.1.{port}"

    

    
        
            
    result = snmp_set(write_community, target, oid, action)
        
    if "INTEGER" in result:
        print("Success")
    else:
        print("Error")
    

    


def run_on_eaton_pdu(ip, port, action):
    
    # SNMP community and target settings
    write_community = 'NCCGWW'
    target = ip  # Replace with your PDU's IP address

    # OID for the PDU outlet status
    oid_turn_off = f"1.3.6.1.4.1.534.6.6.7.6.6.1.3.0.{port}"
    oid_turn_on = f"1.3.6.1.4.1.534.6.6.7.6.6.1.4.0.{port}"
    oid_turn_reboot = f"1.3.6.1.4.1.534.6.6.7.6.6.1.5.0.{port}"

    if action == "0":
        oid = oid_turn_off
    elif action == "1":
        oid = oid_turn_on
    elif action == "2":
        oid = oid_turn_reboot

    switch_feature_on = 2
    change_snmp_ver = True
    
    result = snmp_set(write_community, target, oid, switch_feature_on, change_snmp_ver)
    
    if "INTEGER" in result:
        print("Success")
    else:
        print("Error")



def run_on_ttm(ip, port, action):

    if action == '0':
        action = "off_relays"
    
    if action == '1':
        action = "on_relays"
    
    if action == '2':
        
        command = f"sshpass -p root00 ssh -o StrictHostKeyChecking=no root@{ip} '/root/power_off_relays.sh'"
        dont_print_result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE)
        
        time.sleep(7)
        command = f"sshpass -p root00 ssh -o StrictHostKeyChecking=no root@{ip} '/root/power_on_relays.sh'"
        dont_print_result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE)
        print("Success")

        return None



    
    command = f"sshpass -p root00 ssh -o StrictHostKeyChecking=no root@{ip} '/root/power_{action}.sh'"
    

    try: 
        dont_print_result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE)
        print("Success")
    except subprocess.CalledProcessError as e:
        print(f"Ttm fail error: {e}")


def run_on_ttm_gpio(ip, port, action):

    if action == '0':
        action = "off"
    
    if action == '1':
        action = "on"
    
    if action == '2':
        
        command = f"sshpass -p root00 ssh -o StrictHostKeyChecking=no root@{ip} 'python3 /root/power.py -s off -p {port}'"
        dont_print_result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE)
        
        time.sleep(15)
        command = f"sshpass -p root00 ssh -o StrictHostKeyChecking=no root@{ip} 'python3 /root/power.py -s on -p {port}'"
        dont_print_result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE)
        print("Success")

        return None



    
    command = f"sshpass -p root00 ssh -o StrictHostKeyChecking=no root@{ip} 'python3 /root/power.py -s {action} -p {port}'"
    

    try: 
        dont_print_result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE)
        print("Success")
    except subprocess.CalledProcessError as e:
        print(f"Ttm fail error: {e}")

        
async def main():
    
    # test_ttm = True

    try:
        args = create_parser().parse_args()

        
        if "lab" in args.ip or "ttm" in args.ip:
            ttm_name = check_ttm_device(args.ip)

            if ttm_name == 'ttm_gpio':
                run_on_ttm_gpio(args.ip, args.outlet, args.action)
            else: 
                run_on_ttm(args.ip, args.outlet, args.action)
           
            return None
        
        
        pdu_name = get_pdu_model_from_zabbix(zapi, args.ip)
        
        print(pdu_name)
        zapi.logout()

        # pdu_list_name = await first_to_complete_rec(check_if_altuscn(args.ip, args.outlet, args.action), 
        #                                             check_if_aten(args.ip), 
        #                                             check_if_eaton(args.ip), 
        #                                             check_if_raritan(args.ip))

        # for pdu_name in pdu_list_name:

        if pdu_name == "Altuscn":
            run_on_altuscn_pdu(args.ip, args.outlet, args.action)    
        
        if pdu_name == "Aten":
            run_on_aten_pdu(args.ip, args.outlet, args.action)
        
        if pdu_name == "Raritan":
            run_on_raritan_pdu(args.ip, args.outlet, args.action)

        if pdu_name == "Eaton":
            run_on_eaton_pdu(args.ip, args.outlet, args.action)

            
                
    except Exception as e:
        print(e)  


asyncio.run(main())

