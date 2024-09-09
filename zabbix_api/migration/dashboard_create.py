from zabbix_api import ZabbixAPI
from datetime import datetime
import json

# Connect to the Zabbix API
zapi = ZabbixAPI(server="http://ladjzabbixc.jer.intel.com/zabbix/")
zapi.login("Del_Hosts", "$giga")

def remove_fields(obj, fields_to_remove):
    if isinstance(obj, dict):
        for field in fields_to_remove:
            obj.pop(field, None)
        for value in obj.values():
            remove_fields(value, fields_to_remove)
    elif isinstance(obj, list):
        for item in obj:
            remove_fields(item, fields_to_remove)

def import_zabbix_dashboards(zapi, input_file):

    # Read dashboards from the JSON file
    try:
        with open(input_file, 'r') as f:
            dashboards = json.load(f)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return
    except IOError as e:
        print(f"Error reading file: {str(e)}")
        return

    if not isinstance(dashboards, list):
        print("Error: The JSON file should contain a list of dashboards")
        return

    # Fields to remove before importing
    fields_to_remove = ['dashboardid', 'uuid', 'userid', 'templateid', 'widgetid', 'dashboard_pageid']

    # Import each dashboard
    for dashboard in dashboards:
        # Remove fields that are not needed for creation
        remove_fields(dashboard, fields_to_remove)

        # Ensure 'pages' is present and is a list
        if 'pages' not in dashboard or not isinstance(dashboard['pages'], list):
            print(f"Error: Dashboard '{dashboard.get('name', 'Unknown')}' is missing required 'pages' array")
            continue

        # Ensure 'users' and 'userGroups' are lists if present
        for field in ['users', 'userGroups']:
            if field in dashboard and not isinstance(dashboard[field], list):
                dashboard[field] = [dashboard[field]]

        # Create the dashboard
        try:
            result = zapi.dashboard.create(dashboard)
            print(f"Successfully imported dashboard: {dashboard['name']}")
        except Exception as e:
            print(f"Failed to import dashboard {dashboard.get('name', 'Unknown')}: {str(e)}")

    print(f"Finished importing {len(dashboards)} dashboards")

    # Logout from the Zabbix API
    zapi.logout()





input_file = fr"C:\Scripts\dash1.json"

import_zabbix_dashboards(zapi, input_file)