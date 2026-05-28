from zabbix_api import ZabbixAPI
from datetime import datetime
import json

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "update"
password = "$giga"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

def export_zabbix_discoveries(zapi, output_file):
    try:
        # Get all discovery rules
        discoveries = zapi.drule.get(
            {
                "output": "extend",
                "selectDChecks": "extend"
            }
        )

        # Export discoveries to a JSON file
        with open(output_file, 'w') as f:
            json.dump(discoveries, f, indent=4)

        print(f"Exported {len(discoveries)} discovery rules to {output_file}")

    except Exception as e:
        print(f"Error exporting discovery rules: {str(e)}")

    finally:
        # Logout from the Zabbix API
        zapi.logout()

current_time = datetime.now().strftime("%Y%m%d_%H%M")
output_file = fr"C:\Scripts\discoveries_{current_time}.json"

export_zabbix_discoveries(zapi, output_file)