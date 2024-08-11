from zabbix_api import ZabbixAPI

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "Del_Hosts"
password = "$giga"

# Path to the file containing host names
hosts_file = "hosts.txt"

# Path to the file containing tags (one tag per line, or multiple tags separated by commas)
tags_file = "tags.txt"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

# Read host names
with open(hosts_file, "r") as file:
    host_names = [line.strip() for line in file if line.strip()]

def parse_tags(tags_file):
    """
    Parses tags from the specified file.

    Args:
        tags_file (str): Path to the file containing tags.

    Returns:
        list: A list of dictionaries representing tags.
    """

    tags = []
    with open(tags_file, "r") as file:
        for line in file:
            # Handle multiple tags per line (comma-separated)
            tag_data = line.strip().split(",")
            for tag in tag_data:
                tag_key, tag_value = tag.strip().split("=")
                tags.append({"tag": tag_key, "value": tag_value})
    return tags

# Function to update host tags
def update_host_tags(host_name, requested_tags):
    """
    Updates a host with the specified tags.

    Args:
        host_name (str): Name of the host to update.
        requested_tags (list): List of dictionaries representing tags.
    """

    # Get host ID
    hosts = zapi.host.get({"filter": {"host": host_name}})
    if hosts:
        host_id = hosts[0]["hostid"]
    else:
        print("Host not found:", host_name)
        return  # Skip to the next host if not found

    # Get existing tags (optional, for reference)
    existing_tags = zapi.host.get({"hostids": host_id, "selectTags": "extend"})
    existing_tags = existing_tags[0]["tags"]
    print("Existing tags:", existing_tags)  # Uncomment to print existing tags

    # Remove "automatic" parameter from existing tags (if present)
    existing_tags = [
        {"tag": tag["tag"], "value": tag["value"]} for tag in existing_tags
    ]

    # Check for existing tags (optional)
    # for tag in requested_tags:
    #     if any(existing_tag["tag"] == tag["tag"] for existing_tag in existing_tags):
    #         print(f"Tag '{tag['tag']}' already exists for host {host_name}")
    #         continue  # Skip update if tag already exists (optional)

    # Update tag list (add requested tags)
    existing_tags.extend(requested_tags)

    # Update host with tags
    zapi.host.update(
        {
            "hostid": host_id,
            "tags": existing_tags,
        }
    )

    print(f"Successfully updated host {host_name} with tags.")

for host_name in host_names:
    # Read and parse tags from file
    requested_tags = parse_tags(tags_file)
    update_host_tags(host_name, requested_tags)
