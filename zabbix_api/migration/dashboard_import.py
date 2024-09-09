from zabbix_api import ZabbixAPI
from datetime import datetime
import json

# Connect to the Zabbix API
zapi = ZabbixAPI(server="http://ladjzabbixc.jer.intel.com/zabbix/")
zapi.login("Del_Hosts", "$giga")


def export_zabbix_dashboards(zapi, output_file):

    # Get all dashboards
    dashboards = zapi.dashboard.get(
        {
            "output": "extend",
            "selectPages": "extend",
            "selectUsers": "extend",
            "selectUserGroups": "extend"
        }
    )

    # Export dashboards to a JSON file
    with open(output_file, 'w') as f:
        json.dump(dashboards, f, indent=4)

    print(f"Exported {len(dashboards)} dashboards to {output_file}")

    # Logout from the Zabbix API
    zapi.logout()

current_time = datetime.now().strftime("%Y%m%d_%H%M")


output_file = fr"C:\Scripts\dash_{current_time}.json"

export_zabbix_dashboards(zapi, output_file)