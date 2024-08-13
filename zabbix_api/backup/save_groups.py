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

# Function to retrieve all host groups and their hosts
def get_all_host_groups():
    groups = zapi.hostgroup.get({
        "output": ["groupid", "name"],
        "selectHosts": ["hostid", "host"]
    })
    return groups

# Function to convert host group data to DataFrame
def groups_to_dataframe(groups):
    group_data = []
    for group in groups:
        group_id = group['groupid']
        group_name = group['name']
        hosts = group.get('hosts', [])
        
        if hosts:
            for host in hosts:
                group_data.append({
                    'groupid': group_id,
                    'group_name': group_name,
                    'hostid': host['hostid'],
                    'host_name': host['host']
                })
        else:
            # If no hosts, still add the group with empty host info
            group_data.append({
                'groupid': group_id,
                'group_name': group_name,
                'hostid': '',
                'host_name': ''
            })

    df = pd.DataFrame(group_data)
    return df

# Retrieve all host groups and their hosts
groups = get_all_host_groups()

# Convert group data to DataFrame
groups_df = groups_to_dataframe(groups)

current_time = datetime.now().strftime("%Y%m%d_%H%M")

# Write DataFrame to Excel
output_file = fr"C:\Scripts\host_groups_{current_time}.xlsx"
groups_df.to_excel(output_file, index=False)

print(f"Host groups and their hosts have been successfully written to {output_file}.")