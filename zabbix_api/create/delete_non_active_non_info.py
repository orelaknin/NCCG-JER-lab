from zabbix_api import ZabbixAPI

# Zabbix server configuration
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"
username = "Del_Hosts"
password = "$giga"
hosts_file = "hosts_delete.txt"

# Inventory fields to check
inventory_fields = [
    "alias", "contract_number", "software", "software_app_e",
    "name", "location", "os_short", "hardware", "software_app_a", "software_app_d"
]

# Connect to Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

# Read host names from file
with open(hosts_file, "r") as file:
    host_names = [line.strip() for line in file if line.strip()]

def has_active_connection(host_id):
    """
    Check if host has active connection to Zabbix.
    Returns True if host is monitored and available, False otherwise.
    """
    try:
        hosts = zapi.host.get({
            "output": ["available"],
            "hostids": host_id,
            "monitored_hosts": True
        })
        if hosts and hosts[0].get("available") == "1":
            return True
        return False
    except Exception as e:
        print(f"Error checking connection for host {host_id}: {e}")
        return False

def has_inventory_data(host_id):
    """
    Check if host has any data in specified inventory fields.
    Returns True if any field has data, False if all are empty.
    """
    try:
        inventory = zapi.host.get({
            "output": ["hostid"],
            "selectInventory": inventory_fields,
            "hostids": host_id
        })
        if inventory and inventory[0].get("inventory"):
            inv_data = inventory[0]["inventory"]
            # Check if any inventory field has non-empty value
            for field in inventory_fields:
                if inv_data.get(field) and inv_data[field].strip():
                    return True
        return False
    except Exception as e:
        print(f"Error checking inventory for host {host_id}: {e}")
        return False

def delete_host(host_name):
    """
    Delete host if it has no active connection and no inventory data.
    """
    # Get host ID
    hosts = zapi.host.get({"filter": {"host": host_name}})
    if not hosts:
        print(f"Host not found: {host_name}")
        return
    
    host_id = hosts[0]["hostid"]
    
    # Check conditions
    if has_active_connection(host_id):
        print(f"Skipping {host_name}: Host has active Zabbix connection")
        return
        
    if has_inventory_data(host_id):
        print(f"Skipping {host_name}: Host has inventory data")
        return
    
    # If we reach here, host has no connection and no inventory data
    try:
        zapi.host.delete({"hostid": host_id})
        print(f"Successfully deleted host: {host_name}")
    except Exception as e:
        print(f"Error deleting host {host_name}: {e}")

# Process each host
for host_name in host_names:
    print(f"\nProcessing {host_name}")
    delete_host(host_name)

# Logout
zapi.logout()