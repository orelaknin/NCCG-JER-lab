import pandas as pd
from zabbix_api import ZabbixAPI
from datetime import datetime

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "backup"
password = "$giga"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

# Function to retrieve tags for all hosts
def get_all_host_tags():
    hosts = zapi.host.get({"selectTags": "extend"})
    return hosts

# Function to convert host tags to DataFrame
def tags_to_dataframe(hosts):
    tag_data = []
    for host in hosts:
        host_id = host['hostid']
        host_name = host['host']
        tags = host.get('tags', [])
        
        if tags:
            for tag in tags:
                tag_data.append({
                    'hostid': host_id,
                    'host': host_name,
                    'tag': tag['tag'],
                    'value': tag['value']
                })
        else:
            # If no tags, still add the host with empty tag and value
            tag_data.append({
                'hostid': host_id,
                'host': host_name,
                'tag': '',
                'value': ''
            })

    df = pd.DataFrame(tag_data)
    return df

# Retrieve all host tags
hosts = get_all_host_tags()

# Convert tag data to DataFrame
tags_df = tags_to_dataframe(hosts)

current_time = datetime.now().strftime("%Y%m%d_%H%M")

# Write DataFrame to Excel
output_file = fr"C:\Scripts\host_tags_{current_time}.xlsx"
tags_df.to_excel(output_file, index=False)

print(f"Host tags have been successfully written to {output_file}.")