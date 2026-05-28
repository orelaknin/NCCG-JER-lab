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

def clean_discovery_action(action):
    # Remove fields that might cause issues
    fields_to_remove = ['actionid', 'esc_period', 'pause_suppressed', 'pause_symptoms', 'notify_if_canceled']
    for field in fields_to_remove:
        action.pop(field, None)

    # Ensure all required fields are present
    required_fields = ['name', 'eventsource', 'status']
    for field in required_fields:
        if field not in action:
            raise ValueError(f"Required field '{field}' is missing from the action")

    # Clean operations
    if 'operations' in action:
        cleaned_operations = []
        for operation in action['operations']:
            cleaned_operation = {
                'operationtype': operation['operationtype']
            }
            # Keep 'opgroup' and 'optemplate' if they exist
            if 'opgroup' in operation:
                cleaned_operation['opgroup'] = operation['opgroup']
            if 'optemplate' in operation:
                cleaned_operation['optemplate'] = operation['optemplate']
            cleaned_operations.append(cleaned_operation)
        action['operations'] = cleaned_operations

    # Clean and restructure the filter
    if 'filter' in action:
        cleaned_filter = {
            'evaltype': action['filter'].get('evaltype', '0'),
            'conditions': []
        }
        if 'conditions' in action['filter']:
            for condition in action['filter']['conditions']:
                cleaned_condition = {
                    'conditiontype': condition['conditiontype'],
                    'operator': condition['operator'],
                    'value': condition['value']
                }
                if 'value2' in condition and condition['value2']:
                    cleaned_condition['value2'] = condition['value2']
                cleaned_filter['conditions'].append(cleaned_condition)
        action['filter'] = cleaned_filter

    return action

def import_zabbix_discovery_actions(zapi, input_file):
    try:
        # Read the JSON file
        with open(input_file, 'r') as f:
            actions = json.load(f)

        imported_count = 0
        updated_count = 0
        skipped_count = 0

        for action in actions:
            try:
                cleaned_action = clean_discovery_action(action)

                # Check if an action with the same name already exists
                existing_action = zapi.action.get({
                    "filter": {"name": cleaned_action['name']},
                    "output": ["actionid"]
                })

                if existing_action:
                    # Update existing action
                    cleaned_action['actionid'] = existing_action[0]['actionid']
                    result = zapi.action.update(cleaned_action)
                    updated_count += 1
                    print(f"Updated discovery action: {cleaned_action['name']}")
                else:
                    # Create new action
                    result = zapi.action.create(cleaned_action)
                    imported_count += 1
                    print(f"Created new discovery action: {cleaned_action['name']}")

                print(f"API response: {result}")

            except Exception as e:
                print(f"Error processing discovery action '{action.get('name', 'unknown')}': {str(e)}")
                print(f"Skipping this action.")
                skipped_count += 1

        print(f"Import complete. {imported_count} actions imported, {updated_count} actions updated, {skipped_count} actions skipped.")

    except Exception as e:
        print(f"Error importing discovery actions: {str(e)}")

    finally:
        # Logout from the Zabbix API
        zapi.logout()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_discovery_actions.py <path_to_json_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    import_zabbix_discovery_actions(zapi, input_file)