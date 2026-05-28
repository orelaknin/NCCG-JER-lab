import argparse
from zabbix_api import ZabbixAPI
import time

# Define the Zabbix server URL and login credentials
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"
username = "Del_Hosts"
password = "$giga"

def get_host_id(zapi, hostname):
    """Get the host ID based on the hostname."""
    hosts = zapi.host.get({"filter": {"host": hostname}})
    if hosts:
        return hosts[0]["hostid"]
    else:
        raise ValueError(f"Host with hostname '{hostname}' not found")

def get_script_id(zapi, script_name):
    """Get the script ID based on the script name."""
    scripts = zapi.script.get({"output": "extend", "filter": {"name": script_name}})
    if scripts:
        return scripts[0]["scriptid"]
    else:
        raise ValueError(f"Script with name '{script_name}' not found")

def execute_script(zapi, host_id, script_id):
    """Execute the script and return immediately."""
    try:
        result = zapi.script.execute({
            "scriptid": script_id,
            "hostid": host_id
        })
        print("Script execution initiated...")
        return result
    except Exception as e:
        raise Exception(f"Script execution error: {e}")

def main(hostname):
    """Main function to execute the PDU host power cycle script."""
    zapi = None
    try:
        # Connect to the Zabbix API with shorter timeout
        zapi = ZabbixAPI(server=server_url, timeout=30)  # Reduced timeout to 10 seconds
        zapi.login(username, password)
        
        # Get host ID
        host_id = get_host_id(zapi, hostname)
        print(f"Found host: {hostname}")
        
        # Get script ID
        script_name = "PDU host power cycle"
        script_id = get_script_id(zapi, script_name)
        print("Script found, executing...")
        
        # Execute the script without waiting
        result = execute_script(zapi, host_id, script_id)
        print(f"Execution triggered successfully: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if zapi:
            try:
                zapi.logout()
            except:
                pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Execute "PDU host power cycle" script on a given host.')
    parser.add_argument('hostname', type=str, help='The hostname of the target machine')
    args = parser.parse_args()
    
    main(args.hostname)