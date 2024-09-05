from zabbix_api import ZabbixAPI
import argparse

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "update"
password = "$giga"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

def update_host_groups_and_tags(host_id):
    """
    Remove the maintenance group (ID '22') from the specified host,
    remove the "Group" "Maintenance" tag, and add a new "Group" tag
    based on the software_app_e inventory field.

    Args:
        host_id (str): The ID of the host to update

    Returns:
        None
    """
    maintenance_group_id = '22'
    
    # Get current host groups
    host_groups = zapi.hostgroup.get({"hostids": host_id, "output": ["groupid", "name"]})

    # Remove the maintenance group if present
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

    print(f"Host updated: removed from maintenance group, updated 'Group' tag to '{new_group_value}'")

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
    
def main(host_name):
    """
    Main function to update a host's group membership and tags.

    Args:
        host_name (str): The name of the host to update.
    """
    host_id = get_host_id(host_name)
    if host_id:
        update_host_groups_and_tags(host_id)
    else:
        print(f"Cannot proceed: Host '{host_name}' not found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update host groups and tags.')
    parser.add_argument('hostname', type=str, help='The hostname of the target machine')
    args = parser.parse_args()
    
    main(args.hostname)