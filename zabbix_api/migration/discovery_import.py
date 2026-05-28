from zabbix_api import ZabbixAPI
import json
import sys

# Replace with your Zabbix server URL
server_url = "http://nccg-zabbix.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "Del_Hosts"
password = "$giga"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

def clean_discovery_rule(discovery):
    # Remove fields that might cause issues
    fields_to_remove = ['druleid', 'proxy_hostid']
    for field in fields_to_remove:
        discovery.pop(field, None)

    # Ensure all required fields are present
    required_fields = ['name', 'iprange', 'delay', 'status']
    for field in required_fields:
        if field not in discovery:
            raise ValueError(f"Required field '{field}' is missing from the discovery rule")

    # Clean dchecks
    if 'dchecks' in discovery:
        for dcheck in discovery['dchecks']:
            dcheck.pop('dcheckid', None)
            dcheck.pop('druleid', None)

    return discovery

def import_zabbix_discoveries(zapi, input_file):
    try:
        # Read the JSON file
        with open(input_file, 'r') as f:
            discoveries = json.load(f)

        imported_count = 0
        updated_count = 0

        for discovery in discoveries:
            try:
                cleaned_discovery = clean_discovery_rule(discovery)

                # Check if a discovery rule with the same name already exists
                existing_rule = zapi.drule.get({
                    "filter": {"name": cleaned_discovery['name']},
                    "output": ["druleid"]
                })

                if existing_rule:
                    # Update existing rule
                    cleaned_discovery['druleid'] = existing_rule[0]['druleid']
                    zapi.drule.update(cleaned_discovery)
                    updated_count += 1
                    print(f"Updated discovery rule: {cleaned_discovery['name']}")
                else:
                    # Create new rule
                    zapi.drule.create(cleaned_discovery)
                    imported_count += 1
                    print(f"Created new discovery rule: {cleaned_discovery['name']}")

            except Exception as e:
                print(f"Error processing discovery rule '{discovery.get('name', 'unknown')}': {str(e)}")

        print(f"Import complete. {imported_count} rules imported, {updated_count} rules updated.")

    except Exception as e:
        print(f"Error importing discovery rules: {str(e)}")

    finally:
        # Logout from the Zabbix API
        zapi.logout()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_discoveries.py <path_to_json_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    import_zabbix_discoveries(zapi, input_file)