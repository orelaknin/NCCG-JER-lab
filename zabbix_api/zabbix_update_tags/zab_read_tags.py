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

	 # Check if 'groups' key exists and get the group ID(s) of the host
        if "groups" in host_info[0]:
            groups = host_info[0]["groups"]
            group_ids = [group["groupid"] for group in groups]
            print("Group IDs:", group_ids)
        else:
            print("No group information found for the host")

        # Get the existing tags for the host
        existing_tags = zapi.host.get({"hostids": host_id, "selectTags": "extend"})
        if existing_tags:
            existing_tags = existing_tags[0]["tags"]
            print("Existing Tags:", existing_tags)
        else:
            print("No existing tags found for the host")
    else:
        print("Host not found")

    print("--------------------------")
