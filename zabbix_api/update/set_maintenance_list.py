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


def update_host_groups(host_id):
    """
    Add the host to the maintenance group and update its tags.

    This function performs the following actions:
    1. Checks if the host is already in the maintenance group.
    2. If not, it adds the host to the maintenance group (ID '22').
    3. Updates the host's tags by removing any existing "Group" tag and adding a new "Group" tag with the value "Maintenance".

    Args:
        host_id (str): The ID of the host to update.

    Returns:
        None
    """
    new_group_id = '22'  # ID of the maintenance group
    
    # Get current host groups
    host_groups = zapi.hostgroup.get({"hostids": host_id, "output": ["groupid", "name"]})

    # Check if the host is already in the maintenance group
    new_group = next((group for group in host_groups if group["groupid"] == '22'), None)
    if new_group:
        print("Host is already in maintenance")
        return
    
    # Get existing tags
    existing_tags = zapi.host.get({"hostids": host_id, "selectTags": "extend"})
    existing_tags = existing_tags[0]["tags"]
    
    # Remove "automatic" parameter from existing tags (if present)
    existing_tags = [{k: v for k, v in tag.items() if k != "automatic"} for tag in existing_tags]
    
    # Remove any existing "Group" tag
    existing_tags = [tag for tag in existing_tags if tag.get("tag") != "Group"]

    # Add new "Group" tag with "Maintenance" value
    new_tag = {"tag": "Group", "value": "Maintenance"}
    existing_tags.append(new_tag)
    
    # Update host tags
    zapi.host.update({"hostid": host_id, "tags": existing_tags})

    # Add the host to the maintenance group
    updated_groups = host_groups + [{"groupid": new_group_id}]
    
    # Update the host's groups
    zapi.host.update({
        "hostid": host_id,
        "groups": updated_groups
    })
    print("Host successfully added to maintenance")

def get_host_id(host_name):    
    """
    Retrieve the ID of a host given its name.

    Args:
        host_name (str): The name of the host to look up.

    Returns:
        str: The ID of the host if found, None otherwise.
    """
    hosts = zapi.host.get({"filter": {"host": host_name}})
    if hosts:
        host_id = hosts[0]["hostid"]
        return host_id
    else:
        print(f"Host not found: {host_name}")
        return None
    
def process_host(host_name):
    """
    Process a single host.

    This function retrieves the host ID for the given hostname and then
    updates the host's groups and tags to put it in maintenance.

    Args:
        host_name (str): The name of the host to put in maintenance.
    """
    host_id = get_host_id(host_name)
    if host_id:
        update_host_groups(host_id)
    else:
        print(f"Cannot proceed: Host '{host_name}' not found.")

def main(filename):
    """
    Main function to set multiple hosts in maintenance.

    This function reads hostnames from a file and processes each one.

    Args:
        filename (str): The name of the file containing the list of hostnames.
    """
    try:
        with open(filename, 'r') as file:
            hostnames = file.read().splitlines()
        
        for hostname in hostnames:
            print(f"\nProcessing host: {hostname}")
            process_host(hostname)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Set hosts in maintenance mode in Zabbix.')
    parser.add_argument('filename', type=str, help='The name of the file containing the list of hostnames')
    args = parser.parse_args()
    
    main(args.filename)