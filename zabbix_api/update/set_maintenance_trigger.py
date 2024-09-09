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

def update_host(host_id, original_hostname):
    """
    Update the host: add to maintenance group, update name, update tags, and resolve specific triggers.

    This function performs the following actions:
    1. Checks if the host is already in the maintenance group.
    2. If not, it adds the host to the maintenance group (ID '22').
    3. Updates the host's name by appending "_down".
    4. Updates the host's tags by adding "Group: Maintenance" and "Group: no data" tags.
    5. Resolves specific triggers related to the host.

    Args:
        host_id (str): The ID of the host to update.
        original_hostname (str): The original name of the host.

    Returns:
        None
    """
    maintenance_group_id = '22'  # ID of the maintenance group
    
    # Get current host groups
    host_groups = zapi.hostgroup.get({"hostids": host_id, "output": ["groupid", "name"]})

    # Check if the host is already in the maintenance group
    in_maintenance = any(group["groupid"] == maintenance_group_id for group in host_groups)
    if in_maintenance:
        print("Host is already in maintenance")
        return
    
    # Get existing tags
    existing_tags = zapi.host.get({"hostids": host_id, "selectTags": "extend"})
    existing_tags = existing_tags[0]["tags"]
    
    # Remove "automatic" parameter from existing tags (if present)
    existing_tags = [{k: v for k, v in tag.items() if k != "automatic"} for tag in existing_tags]
    
    # Remove any existing "Group" tags
    existing_tags = [tag for tag in existing_tags if tag.get("tag") != "Group"]

    # Add new "Group" tags
    new_tags = [
        {"tag": "Group", "value": "Maintenance"},
    ]
    existing_tags.extend(new_tags)
    
    # Update host name, tags, and groups
    updated_groups = host_groups + [{"groupid": maintenance_group_id}]
    new_hostname = f"{original_hostname}_down"
    
    zapi.host.update({
        "hostid": host_id,
        "host": new_hostname,  # This updates the {HOST.HOST} field
        "name": new_hostname,  # This updates the visible name
        "tags": existing_tags,
        "groups": updated_groups
    })
    
    print(f"Host successfully updated: added to maintenance, renamed to '{new_hostname}', and tags updated")

    # Resolve specific triggers
    resolve_triggers(host_id)

def get_host_id(host_name):    
    """
    Retrieve the ID and original name of a host given its name.

    Args:
        host_name (str): The name of the host to look up.

    Returns:
        tuple: (host_id, original_hostname) if found, (None, None) otherwise.
    """
    hosts = zapi.host.get({"filter": {"host": host_name}, "output": ["hostid", "host"]})
    if hosts:
        return hosts[0]["hostid"], hosts[0]["host"]
    else:
        print(f"Host not found: {host_name}")
        return None, None

def resolve_triggers(host_id):
    """
    Resolve specific triggers for the given host.

    Args:
        host_id (str): The ID of the host.

    Returns:
        None
    """
    # Get triggers for the host
    triggers = zapi.trigger.get({
        "hostids": host_id,
        "selectTags": "extend",
        "output": ["triggerid", "description", "value"]
    })

    for trigger in triggers:
        if any( tag["tag"] == "maintenance" and tag["value"] == "keep" for tag in trigger["tags"] ):
            continue
        if trigger["value"] == "1":  # If the trigger is in PROBLEM state
            zapi.event.acknowledge({
                "eventids": zapi.trigger.get({
                    "triggerids": trigger["triggerid"],
                    "output": ["lastEvent"],
                    "selectLastEvent": ["eventid"]
                })[0]["lastEvent"]["eventid"],
                "action": 1,  # Close problem
                "message": "Resolved automatically due to host maintenance"
            })
            print(f"Resolved trigger: {trigger['description']}")

def main(host_name):
    """
    Main function to update a host's maintenance status, name, tags, and resolve triggers.

    This function retrieves the host ID for the given hostname, updates the host's groups,
    name, and tags to put it in maintenance, and resolves specific triggers.

    Args:
        host_name (str): The name of the host to update.
    """
    host_id, original_hostname = get_host_id(host_name)
    if host_id:
        update_host(host_id, original_hostname)
    else:
        print(f"Cannot proceed: Host '{host_name}' not found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Set host in maintenance mode, update name, add tags, and resolve triggers in Zabbix.')
    parser.add_argument('hostname', type=str, help='The hostname of the target machine to update')
    args = parser.parse_args()
    
    main(args.hostname)