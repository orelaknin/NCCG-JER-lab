import pandas as pd
from zabbix_api import ZabbixAPI
from datetime import datetime

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "Del_Hosts"
password = "$giga"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

# Function to retrieve inventory for all hosts
def get_all_host_inventories():
    hosts = zapi.host.get({"selectInventory": "extend"})
    return hosts

# Function to enable manual inventory mode and retrieve inventory data
def inventory_to_dataframe(hosts):
    inventory_data = []
    for host in hosts:
        host_id = host['hostid']
        
      
        
        # Retrieve the inventory after setting the mode
        host_inventory = host.get('inventory', {})
        if isinstance(host_inventory, dict):  # Check if the inventory is a dictionary
            host_inventory['hostid'] = host_id
            host_inventory['host'] = host['host']
            inventory_data.append(host_inventory)
        else:
            print(f"Unexpected inventory format for host '{host['host']}' (ID: {host_id}): {host_inventory}")

    df = pd.DataFrame(inventory_data)
    return df

# Retrieve all host inventories
hosts = get_all_host_inventories()

# Convert inventory data to DataFrame
inventory_df = inventory_to_dataframe(hosts)

current_time = datetime.now().strftime("%Y%m%d_%H%M")

# Write DataFrame to Excel
output_file = fr"C:\Scripts\host_inventories_{current_time}.xlsx"
inventory_df.to_excel(output_file, index=False)

print(f"Host inventories have been successfully written to {output_file}.")
