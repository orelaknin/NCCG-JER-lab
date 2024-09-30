from zabbix_api import ZabbixAPI
import json

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "update"
password = "$giga"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

def import_zabbix_host_groups(zapi, input_file):

    try:
        # Read host groups from the JSON file
        with open(input_file, 'r') as f:
            host_groups = json.load(f)

        if not isinstance(host_groups, list):
            print("Error: The JSON file should contain a list of host groups")
            return

        # Fields to remove before importing
        fields_to_remove = ['groupid','flags','uuid']

        # Import each host group
        for host_group in host_groups:
            # Remove fields that are not needed for creation
            for field in fields_to_remove:
                host_group.pop(field, None)

            # Create the host group
            try:
                result = zapi.hostgroup.create(host_group)
                print(f"Successfully imported host group: {host_group['name']}")
            except Exception as e:
                print(f"Failed to import host group {host_group.get('name', 'Unknown')}: {str(e)}")
                print(f"Host group data: {json.dumps(host_group, indent=2)}")

        print(f"Finished importing {len(host_groups)} host groups")

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
    except IOError as e:
        print(f"Error reading file: {str(e)}")
    except Exception as e:
        print(f"Error importing host groups: {str(e)}")

    finally:
        # Logout from the Zabbix API
        zapi.logout()

input_file = fr"C:\Scripts\groups_.json"

import_zabbix_host_groups(zapi, input_file)