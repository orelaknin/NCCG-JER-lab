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

# Define inventory fields of interest and their display names
inventory_fields_of_interest = {
    "hardware": "PDU IP",
    "software_app_a": "PDU Port",
    "location": "Location"
    # Add more mappings as needed, e.g.:
    # "type": "Type",
    # "model": "Model",
    # "serial": "Serial Number",
    # "tag": "Tag",
    # "asset_tag": "Asset Tag",
    # "location": "Location",
    # "site_address_a": "Site Address",
}

# Define items of interest
items_of_interest = [
    "get_ip_address",
    # Add more items as needed, e.g.:
    # "Generic SNMP: System description",
    # "SNMP agent availability",
    # "System uptime",
]

def get_host_info(zapi, hostname):
    try:
        hosts = zapi.host.get({
            "output": ["hostid", "name"],
            "selectInterfaces": ["ip"],
            "selectInventory": list(inventory_fields_of_interest.keys()),
            "selectItems": ["itemid", "name", "key_", "lastvalue"],
            "filter": {
                "host": hostname
            }
        })
        
        if not hosts:
            print(f"No host found with hostname: {hostname}")
            return None
        
        host = hosts[0]
        
        # Fetch inventory fields
        inventory = {inventory_fields_of_interest[k]: v for k, v in host['inventory'].items() if v}
        
        # Fetch specific items
        items = {item['name']: item['lastvalue'] for item in host['items'] if item['name'] in items_of_interest}
        
        # Get the IP address
        ip_address = host['interfaces'][0]['ip'] if host['interfaces'] else "N/A"
        
        return {
            "Hostname": hostname,
            "IP": ip_address,
            "Inventory": inventory,
            "Items": items
        }
        
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

def main():
    hostname = input("Enter the hostname to check: ")
    
    if zapi:
        result = get_host_info(zapi, hostname)
        if result:
            print("\nHost Information:")
            print(f"Hostname: {result['Hostname']}")
            print(f"IP: {result['IP']}")
            
            print("\nInventory Fields:")
            for key, value in result['Inventory'].items():
                print(f"{key}: {value}")
            
            print("\nItem Fields:")
            for key, value in result['Items'].items():
                print(f"{key}: {value}")
        
        zapi.logout()

if __name__ == "__main__":
    main()