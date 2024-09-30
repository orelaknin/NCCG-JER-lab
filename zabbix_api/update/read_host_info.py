from zabbix_api import ZabbixAPI

# Connect to the Zabbix API
zapi = ZabbixAPI(server="http://ladjzabbixc.jer.intel.com/zabbix")
zapi.login("Del_Hosts", "$giga")

print("--------------------------")

# Read host names from the text file
try:
    with open("hosts.txt", "r") as file:
        host_names = [line.strip() for line in file if line.strip()]
except FileNotFoundError:
    print("Error: hosts.txt file not found.")
    exit(1)

# Get information for each host from the Zabbix server
for host_name in host_names:
    print("Host:", host_name)

    # Get the ID of the host
    host_info = zapi.host.get({
        "filter": {"host": host_name},
        "selectGroups": "extend",
        "selectParentTemplates": ["templateid", "name"],
        "output": ["hostid", "name"]
    })

    if host_info:
        host_id = host_info[0]["hostid"]
        print("Host ID:", host_id)

        # Get the group IDs and names of the host
        groups = host_info[0].get("groups", [])
        if groups:
            group_details = [(group["groupid"], group["name"]) for group in groups]
            print("Group IDs and Names:", group_details)
        else:
            print("No group information found for the host")

        # Get the template IDs and names of the host
        templates = host_info[0].get("parentTemplates", [])
        if templates:
            template_details = [(template["templateid"], template["name"]) for template in templates]
            print("Template IDs and Names:", template_details)
        else:
            print("No template information found for the host")

        # Get the existing tags for the host
        existing_tags_info = zapi.host.get({
            "hostids": host_id,
            "selectTags": "extend",
            "output": ["hostid"]
        })
        
        if existing_tags_info:
            existing_tags = existing_tags_info[0].get("tags", [])
            if existing_tags:
                print("Existing Tags:", existing_tags)
            else:
                print("No existing tags found for the host")
        else:
            print("Error fetching tags information.")
    else:
        print("Host not found")

    print("--------------------------")
