from zabbix_api import ZabbixAPI
import sys

# Connect to the Zabbix API
zapi = ZabbixAPI(server="http://ladjzabbixc.jer.intel.com/zabbix/")
zapi.login("Del_Hosts", "$giga")

# Read host names from the text file
with open("hosts.txt", "r") as file:
    host_names = [line.strip() for line in file if line.strip()]

# Get information for each host from the Zabbix server
for host_name in host_names:
    print("Host:", host_name)

    # Get the ID of the host
    host_info = zapi.host.get({"filter": {"host": host_name}})
    if host_info:
        host_id = host_info[0]["hostid"]
        print("Host ID:", host_id)

        # Get the existing tags for the host
        existing_inv = zapi.host.get({"hostids": host_id, "selectInventory": "extend"})
        if existing_inv:
            existing_inv = existing_inv[0]["inventory"]
            print("Existing inventory:", existing_inv)
        else:
            print("No existing inventory found for the host")
    else:
        print("Host not found")

    print("--------------------------")
