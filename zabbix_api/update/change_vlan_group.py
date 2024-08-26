from zabbix_api import ZabbixAPI
import ipaddress
import re

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "update"
password = "$giga"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

def get_discovery_rules():
    # Fetch all discovery rules
    discovery_rules = zapi.drule.get({
        "output": ["druleid", "name", "iprange"],
        "selectDChecks": ["type", "key_", "ports"],
        "filter": {"status": [0, 1]}
    })
    
    vlan_ranges = []
    for rule in discovery_rules:
        vlan_ranges.append({
            "name": rule["name"],
            "range": rule["iprange"]
        })
    return vlan_ranges

def get_vlan_group(ip_address, vlan_ranges):
    ip_addr = ipaddress.ip_address(ip_address)
    for vlan in vlan_ranges:
        for ip_range in vlan["range"].split(','):
            ip_range = ip_range.strip()
            try:
                if '-' in ip_range:
                    # Handle IP range (e.g., "10.12.236.4-254")
                    start, end = ip_range.split('-')
                    start_ip = ipaddress.ip_address(start.strip())
                    
                    # Handle the shorthand notation for the end IP
                    if '.' not in end:
                        # If end doesn't contain dots, it's just the last octet
                        end_ip = ipaddress.ip_address(start_ip.packed[:3] + bytes([int(end)]))
                    else:
                        end_ip = ipaddress.ip_address(end.strip())
                    
                    if start_ip <= ip_addr <= end_ip:
                        return vlan["name"]
                elif '/' in ip_range:
                    # Handle CIDR notation (e.g., "10.12.172.4/23")
                    network = ipaddress.ip_network(ip_range, strict=False)
                    if ip_addr in network:
                        return vlan["name"]
                else:
                    # Handle single IP
                    if ip_addr == ipaddress.ip_address(ip_range):
                        return vlan["name"]
            except ValueError as e:
                print(f"Warning: Could not parse IP range {ip_range} in VLAN {vlan['name']}: {e}")
                continue
    return None

# Add this function to print out the discovery rules for debugging
#def print_discovery_rules(vlan_ranges):
    print("Discovery Rules:")
    for vlan in vlan_ranges:
        print(f"Name: {vlan['name']}, Range: {vlan['range']}")
    print()

# In your main script, after fetching the discovery rules:
vlan_ranges = get_discovery_rules()
#print_discovery_rules(vlan_ranges)

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
    
    # Filter out VLAN groups (assuming VLAN groups are the same as discovery rule names)
    non_vlan_groups = [group for group in host_groups if group["name"] not in [vlan["name"] for vlan in vlan_ranges]]
    
    # Add the new VLAN group
    updated_groups = non_vlan_groups + [{"groupid": new_group_id}]
    
    # Update the host's groups
    zapi.host.update({
        "hostid": host_id,
        "groups": updated_groups
    })

# Get discovery rules and their IP ranges
vlan_ranges = get_discovery_rules()


# Get specific host (for testing)
hosts = zapi.host.get({
    "output": ["hostid", "host"],
    "selectInterfaces": ["ip"]
})

for host in hosts:
    host_id = host["hostid"]
    host_name = host["host"]
    
    # Get the host's IP address (assumes the first interface is the main one)
    if host["interfaces"]:
        ip_address = host["interfaces"][0]["ip"]
        
        # Determine the VLAN group
        vlan_group = get_vlan_group(ip_address, vlan_ranges)
        
        if vlan_group:
            print(f"Updating {host_name} ({ip_address}) to group {vlan_group}")
            update_host_groups(host_id, vlan_group)
        else:
            print(f"No matching VLAN found for {host_name} ({ip_address})")
    else:
        print(f"No IP address found for {host_name}")

print("Host group updates completed.")