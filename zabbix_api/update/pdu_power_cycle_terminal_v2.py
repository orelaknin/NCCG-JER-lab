#!/usr/bin/env python3
# Title: Zabbix PDU Power Cycle Script
# Description: This script interacts with the Zabbix API to execute PDU power cycle scripts
#              for a specified host. It supports host-only, board-only, or combined
#              board+host power cycles based on inventory data and command-line arguments.
# Author: Orel Aknin
# Date: April 21, 2025

import argparse
from zabbix_api import ZabbixAPI
import re

server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"
username = "Del_Hosts"
password = "$giga"

def get_host_id(zapi, hostname):
    hosts = zapi.host.get({"filter": {"host": hostname}})
    if hosts:
        return hosts[0]["hostid"]
    else:
        raise ValueError(f"Host with hostname '{hostname}' not found")

def get_script_id(zapi, script_name):
    scripts = zapi.script.get({"output": "extend", "filter": {"name": script_name}})
    if scripts:
        return scripts[0]["scriptid"]
    else:
        raise ValueError(f"Script with name '{script_name}' not found")

def execute_script(zapi, host_id, script_id):
    result = zapi.script.execute({"scriptid": script_id, "hostid": host_id})
    return result

def get_board_port(zapi, hostname):
    hosts = zapi.host.get({
        "output": ["hostid"],
        "selectInventory": ["type_full"],
        "filter": {"host": hostname}
    })
    if hosts and "inventory" in hosts[0] and "type_full" in hosts[0]["inventory"]:
        type_full = hosts[0]["inventory"]["type_full"]
        match = re.search(r'\d+', type_full)
        if match:
            return int(match.group(0))
    return None

def alert_pdu_power_cycle_failure():
    print('Power Cycle PDU Zabbix failed. Try locally by running [pwc ipmi cycle ] or [pwc_ipmi cycle]')

def main(hostname, host_only, board_only):
    """
    Main function to execute the appropriate power cycle script on a given host.

    Args:
        hostname (str): The name of the host on which to execute the script.
        host_only (bool): If True, execute 'PDU host power cycle' only.
        board_only (bool): If True, execute 'PDU Board power cycle' only.

    Note:
        If neither host_only nor board_only is specified, the default script
        "PDU Board+Host power cycle" is executed if a board port is found in
        inventory.type_full; otherwise, it falls back to "PDU host power cycle".
        The Board+Host sequence:
        1. Turns off the board (using the port from inventory.type_full).
        2. Turns off the host (using the outlet specified in the PDU configuration).
        3. Waits for a delay (default 10 seconds).
        4. Turns on the board.
        5. Turns on the host.
    """
    try:
        zapi = ZabbixAPI(server=server_url, timeout=60)
        zapi.login(username, password)
        
        host_id = get_host_id(zapi, hostname)
        
        if host_only:
            script_name = "PDU host power cycle"
        elif board_only:
            script_name = "PDU Board power cycle"
        else:
            board_port = get_board_port(zapi, hostname)
            if board_port is not None:
                script_name = "PDU Board+Host power cycle"
                print(f"Board port found ({board_port}), using 'PDU Board+Host power cycle'")
            else:
                script_name = "PDU host power cycle"
                print(f"No board port found in PDU board port, falling back to 'PDU host power cycle'")
        
        script_id = get_script_id(zapi, script_name)
        result = execute_script(zapi, host_id, script_id)
        if "error" in result or not result.get("value"):
            alert_pdu_power_cycle_failure()
        else:
            print(f"Script execution result for '{script_name}': {result}")
    
    except Exception as e:
        alert_pdu_power_cycle_failure()
        print(f"Error: {str(e)}")
    
    finally:
        zapi.logout()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Execute a PDU power cycle script on a given host via Zabbix API. '
                    'By default (no flags), runs "PDU Board+Host power cycle" if a board port '
                    'is found in "PDU board port" field (turns off board, turns off host, waits 10s, '
                    'turns on board, turns on host), otherwise runs "PDU host power cycle".'
    )
    parser.add_argument('hostname', type=str, help='The hostname of the target machine')
    parser.add_argument('-host', '--host-only', action='store_true', help='Power cycle the host only (runs "PDU host power cycle")')
    parser.add_argument('-board', '--board-only', action='store_true', help='Power cycle the board only (runs "PDU Board power cycle")')

    args = parser.parse_args()

    if args.host_only and args.board_only:
        parser.error("Arguments -host/--host-only and -board/--board-only are mutually exclusive")

    main(args.hostname, args.host_only, args.board_only)