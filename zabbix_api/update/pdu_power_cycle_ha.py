import subprocess
import socket
import argparse
import time
import pexpect
import asyncio
import logging
import sys
import os



sys.stderr = open(os.devnull, 'w')


haifa_script_path = "/home/laduser/haifa_script_altuscn/haifa_altuscn.py"
password_haifa = "$giga"



final_break_flag = None


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

    parser = argparse.ArgumentParser("new_pdu_script.py")

    parser.add_argument("-i", "--ip", help="ip address", required=True)
    parser.add_argument("-o", "--outlet", help="optional flag for remote json file", required=True)
    parser.add_argument("-a", "--action", help="action to perform (on, off, cycle)", required=True)

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

        ssh_command = f"sshpass -p '{password_haifa}' ssh -o StrictHostKeyChecking=no laduser@143.185.151.13 '{remote_command}'"

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
        else:
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

    # OID for the PDU outlet status
    oid = f"1.3.6.1.4.1.21317.1.3.2.2.2.2.{int(port) + 1}.0"

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


        
async def main():

    try:

        args = create_parser().parse_args()

        #run_on_ttm(args.ip, args.outlet, args.action)
        
        #return None

        if "lab" in args.ip or "ttm" in args.ip:
            run_on_ttm(args.ip, args.outlet, args.action)
           
            return None
        
        pdu_list_name = await first_to_complete_rec(check_if_altuscn(args.ip, args.outlet, args.action), 
                                                    check_if_aten(args.ip), 
                                                    check_if_eaton(args.ip), 
                                                    check_if_raritan(args.ip))

        for pdu_name in pdu_list_name:

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

