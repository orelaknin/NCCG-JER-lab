from zabbix_api import ZabbixAPI
import pandas as pd
import time
from requests.exceptions import Timeout, RequestException
from datetime import datetime

def zabbix_login(url, username, password, timeout=30):
    try:
        zapi = ZabbixAPI(server=url, timeout=timeout)
        zapi.login(username, password)
        print(f"Connected to Zabbix API Version {zapi.api_version()}")
        return zapi
    except Exception as e:
        print(f"Error connecting to Zabbix API: {e}")
        return None


def get_top_hosts_data(zapi):
    all_hosts = []
    
    try:
        hosts = zapi.host.get({
            "output": ["hostid", "name", "status"],
            "selectInterfaces": ["ip"],
            "selectInventory": [
                "alias", "contract_number", "software", "software_app_e",
                "name", "location", "os_short", "hardware", "software_app_a","software_app_d"
            ],
            "sortfield": "hostid",
            "sortorder": "ASC",
        })
        if not hosts:
            print(f"No hosts macthed")
            return None
            
        all_hosts.extend(hosts)
        print(f"Retrieved {len(all_hosts)} hosts")
        
        
    except Timeout:
        print(f"Timeout occurred. Retrying in 5 seconds...")
        time.sleep(5)
        return None
    except RequestException as e:
        print(f"Error occurred: {e}. Retrying in 5 seconds...")
        time.sleep(5)
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

    result = []
    for host in all_hosts:
        host_data = process_host_data(host)
        result.append(host_data)

    return result

def process_host_data(host):
    
    host_data = {
    "System Availability": "Up (1)" if host['status'] == '0' else "Down (2)",
    "Host": host['name'],
    "IP": host['interfaces'][0]['ip'] if host['interfaces'] else "",
    "Nuc Hostname": host['inventory'].get('alias', '') if isinstance(host['inventory'], dict) else '',
    "Link Partner": host['inventory'].get('contract_number', '') if isinstance(host['inventory'], dict) else '',
    "Host Type": host['inventory'].get('software_app_d', '') if isinstance(host['inventory'], dict) else '',
    "Group": host['inventory'].get('software_app_e', '') if isinstance(host['inventory'], dict) else '',
    "Assign to": host['inventory'].get('name', '') if isinstance(host['inventory'], dict) else '',
    "Location": host['inventory'].get('location', '') if isinstance(host['inventory'], dict) else '',
    "Accessories": host['inventory'].get('os_short', '') if isinstance(host['inventory'], dict) else '',
    "PDU IP": host['inventory'].get('hardware', '') if isinstance(host['inventory'], dict) else '',
    "PDU Host Port": host['inventory'].get('software_app_a', '') if isinstance(host['inventory'], dict) else '',
}


    return host_data
current_time = datetime.now().strftime("%Y%m%d_%H%M")
def export_to_excel(data, filename="all_hosts_inv"+"_"+current_time+".xlsx"):
    if not data:
        print("No data to export")
        return
    
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"Data exported to {filename}")


def main():
    url =  "http://ladjzabbixc.jer.intel.com/zabbix/"
    username = "backup"
    password = "$giga"
    
    zapi = zabbix_login(url, username, password)
    if zapi:
        data = get_top_hosts_data(zapi)
        if data:
            export_to_excel(data)
        zapi.logout()

if __name__ == "__main__":
    main()