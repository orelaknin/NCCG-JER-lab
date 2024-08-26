import argparse
from zabbix_api import ZabbixAPI

# Define the Zabbix server URL and login credentials
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"
username = "Del_Hosts"
password = "$giga"

def get_host_id(zapi, hostname):
    """
    Get the host ID based on the hostname.

    Args:
        zapi (ZabbixAPI): An authenticated instance of ZabbixAPI.
        hostname (str): The name of the host to retrieve the ID for.

    Returns:
        str: The ID of the host.

    Raises:
        ValueError: If the host with the specified hostname is not found.
    """
    hosts = zapi.host.get({"filter": {"host": hostname}})
    if hosts:
        return hosts[0]["hostid"]
    else:
        raise ValueError(f"Host with hostname '{hostname}' not found")

def get_script_id(zapi, script_name):
    """
    Get the script ID based on the script name.

    Args:
        zapi (ZabbixAPI): An authenticated instance of ZabbixAPI.
        script_name (str): The name of the script to retrieve the ID for.

    Returns:
        str: The ID of the script.

    Raises:
        ValueError: If the script with the specified name is not found.
    """
    scripts = zapi.script.get({"output": "extend", "filter": {"name": script_name}})
    if scripts:
        return scripts[0]["scriptid"]
    else:
        raise ValueError(f"Script with name '{script_name}' not found")

def execute_script(zapi, host_id, script_id):
    """
    Execute the script on the specified host.

    Args:
        zapi (ZabbixAPI): An authenticated instance of ZabbixAPI.
        host_id (str): The ID of the host on which to execute the script.
        script_id (str): The ID of the script to execute.

    Returns:
        dict: The result of the script execution.
    """
    result = zapi.script.execute({"scriptid": script_id, "hostid": host_id})
    return result

def main(hostname):
    """
    Main function to execute the "new PDU host power cycle" script on a given host.

    Args:
        hostname (str): The name of the host on which to execute the script.
    """
    try:
        # Connect to the Zabbix API
        zapi = ZabbixAPI(server=server_url)
        zapi.login(username, password)
        
        # Get host ID
        host_id = get_host_id(zapi, hostname)
        # print(f"Host ID for '{hostname}': {host_id}")
        
        # Get script ID for "new PDU host power cycle"
        script_name = "PDU host power cycle"
        script_id = get_script_id(zapi, script_name)
        # print(f"Script ID for '{script_name}': {script_id}")
        
        # Execute the script on the host
        result = execute_script(zapi, host_id, script_id)
        print(f"Script execution result: {result}")
    
    finally:
        # Logout from the Zabbix API
        zapi.logout()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Execute "PDU host power cycle" script on a given host.')
    parser.add_argument('hostname', type=str, help='The hostname of the target machine')
    args = parser.parse_args()
    
    main(args.hostname)