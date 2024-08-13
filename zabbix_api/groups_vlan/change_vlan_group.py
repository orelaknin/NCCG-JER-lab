import ipaddress
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


def get_vlan_group(ip_address):
    for vlan in vlan_ranges:
        try:
            # Try to create an IP network object
            network = ipaddress.ip_network(vlan["range"], strict=False)
            if ipaddress.ip_address(ip_address) in network:
                return vlan["name"]
        except ValueError:
            # If it's not a valid network, try as an IP range
            start, end = vlan["range"].split('-')
            start_ip = ipaddress.ip_address(start.strip())
            end_ip = ipaddress.ip_address(end.strip())
            if start_ip <= ipaddress.ip_address(ip_address) <= end_ip:
                return vlan["name"]
    return None

# Update your vlan_ranges to use either CIDR notation or IP ranges
vlan_ranges = [
    {"name": "FW Lab 112", "range": "10.12.112.4/23"},
    {"name": "Tech Room 236", "range": "10.12.236.4/24"},
    # Add more VLAN ranges as needed
]

def update_host_groups(host_id, new_group_name):
    # Get all groups
    all_groups = zapi.hostgroup.get({"output": ["groupid", "name"]})
    
    # Find or create the new group
    new_group = next((group for group in all_groups if group["name"] == new_group_name), None)
    if not new_group:
        new_group = zapi.hostgroup.create({"name": new_group_name})
        new_group_id = new_group["groupids"][0]
    else:
        new_group_id = new_group["groupid"]
    
    # Get current host groups
    host_groups = zapi.hostgroup.get({"hostids": host_id, "output": ["groupid", "name"]})
    
    # Filter out VLAN groups
    non_vlan_groups = [group for group in host_groups if not any(vlan["name"] in group["name"] for vlan in vlan_ranges)]
    
    # Add the new VLAN group
    updated_groups = non_vlan_groups + [{"groupid": new_group_id}]
    
    # Update the host's groups
    zapi.host.update({
        "hostid": host_id,
        "groups": updated_groups
    })

# Get all hosts
hosts = zapi.host.get({"filter": {"host": "ladjoreltech"}, "output": ["hostid", "host"], "selectInterfaces": ["ip"]})

for host in hosts:
    host_id = host["hostid"]
    host_name = host["host"]
    
    # Get the host's IP address (assumes the first interface is the main one)
    if host["interfaces"]:
        ip_address = host["interfaces"][0]["ip"]
        
        # Determine the VLAN group
        vlan_group = get_vlan_group(ip_address)
        
        if vlan_group:
            print(f"Updating {host_name} ({ip_address}) to group {vlan_group}")
            update_host_groups(host_id, vlan_group)
        else:
            print(f"No matching VLAN found for {host_name} ({ip_address})")
    else:
        print(f"No IP address found for {host_name}")

print("Host group updates completed.")