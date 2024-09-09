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

def import_zabbix_scripts(zapi , input_file):

    try:
        # Read scripts from the JSON file
        with open(input_file, 'r') as f:
            scripts = json.load(f)

        if not isinstance(scripts, list):
            print("Error: The JSON file should contain a list of scripts")
            return

        # Fields to remove before importing
        fields_to_remove = ['scriptid', 'hosts','timeout','port', 'authtype', 'username', 'password', 'publickey', 'privatekey', 'menu_path', 'url', 'new_window', 'parameters']

        # Import each script
        for script in scripts:
            # Remove fields that are not needed for creation
            for field in fields_to_remove:
                script.pop(field, None)

            # Convert group IDs to names if present
            if 'groups' in script:
                script['groups'] = [{"name": group['name']} for group in script['groups']]

            # Create the script
            try:
                result = zapi.script.create(script)
                print(f"Successfully imported script: {script['name']}")
            except Exception as e:
                print(f"Failed to import script {script.get('name', 'Unknown')}: {str(e)}")
                print(f"Script data: {json.dumps(script, indent=2)}")

        print(f"Finished importing {len(scripts)} scripts")

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
    except IOError as e:
        print(f"Error reading file: {str(e)}")
    except Exception as e:
        print(f"Error importing scripts: {str(e)}")

    finally:
        # Logout from the Zabbix API
        zapi.logout()

input_file = fr"C:\Scripts\scripts_.json"

import_zabbix_scripts(zapi, input_file)