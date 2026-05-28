from zabbix_api import ZabbixAPI
import argparse

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"
username = "update"
password = "$giga"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

def update_host_groups_and_tags(host_id):
    """
    Remove the maintenance group (ID '22') from the specified host if present,
    remove the "Group" "Maintenance" tag, and add a new "Group" tag
    based on the software_app_e inventory field.
    """
    maintenance_group_id = '22'
    
    # Get current host groups
    host_groups = zapi.hostgroup.get({"hostids": host_id, "output": ["groupid", "name"]})
    
    # Check if host is in maintenance group
    is_in_maintenance = any(group["groupid"] == maintenance_group_id for group in host_groups)
    
    if not is_in_maintenance:
        return  # Skip if host isn't in maintenance group
    
    # Remove the maintenance group
    updated_groups = [group for group in host_groups if group["groupid"] != maintenance_group_id]
    
    # Update the host's groups
    zapi.host.update({
        "hostid": host_id,
        "groups": updated_groups
    })

    # Get existing tags and inventory
    host_data = zapi.host.get({
        "hostids": host_id,
        "selectTags": "extend",
        "selectInventory": ["software_app_e"]
    })[0]

    existing_tags = host_data["tags"]
    inventory = host_data["inventory"]

    # Remove "automatic" parameter and "Group" tag from existing tags
    updated_tags = [tag for tag in existing_tags if tag.get("tag") != "Group" and "automatic" not in tag]

    # Get the new group value from software_app_e inventory field
    new_group_value = inventory.get("software_app_e", "")

    # Add new "Group" tag with value from software_app_e
    if new_group_value:
        new_tag = {"tag": "Group", "value": new_group_value}
        updated_tags.append(new_tag)

    # Update host tags
    zapi.host.update({
        "hostid": host_id,
        "tags": updated_tags
    })

    print(f"Host {host_id} updated: removed from maintenance group, updated 'Group' tag to '{new_group_value}'")

def get_host_id(host_name):    
    """
    Retrieve the ID of the host with the given name

    Args:
        host_name (str): The name of the host to retrieve the ID for

    Returns:
        str: The ID of the host, or None if the host is not found
    """
    hosts = zapi.host.get({"filter": {"host": host_name}})
    if hosts:
        host_id = hosts[0]["hostid"]
        return host_id
    else:
        print("Host not found:", host_name)
        return None

def process_all_hosts():
    """
    Process all hosts and remove maintenance mode only for those currently in it
    """
    # Get all hosts with their group information
    hosts = zapi.host.get({
        "output": ["hostid", "host"],
        "selectInterfaces": ["ip"],
        "selectGroups": ["groupid", "name"]  # Added to check group membership
    })

    for host in hosts:
        host_id = host["hostid"]
        host_name = host["host"]
        try:
            update_host_groups_and_tags(host_id)
        except Exception as e:
            print(f"Failed to process host {host_name} ({host_id}): {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Remove hosts from maintenance mode.')
    parser.add_argument('--all', action='store_true', help='Process all hosts')
    parser.add_argument('--hostname', type=str, nargs='?', help='Process single hostname')
    
    args = parser.parse_args()
    
    if args.all:
        process_all_hosts()
    elif args.hostname:
        host_id = get_host_id(args.hostname)
        if host_id:
            update_host_groups_and_tags(host_id)
    else:
        parser.print_help()