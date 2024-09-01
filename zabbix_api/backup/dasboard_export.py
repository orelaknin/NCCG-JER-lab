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

host_tag=input("Enter the group to export:")

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
            "selectItems": ["itemid", "name", "key_", "lastvalue"],
            "sortfield": "hostid",
            "sortorder": "ASC",
            "tags": [
                {
                    "tag": "Group",
                    "value": host_tag,        
                }
            ],
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
        "System Name": host['name'],
        "IP": host['interfaces'][0]['ip'] if host['interfaces'] else "",
        "Nuc Hostname": host['inventory'].get('alias', ''),
        "Link Partner": host['inventory'].get('contract_number', ''),
        "Host Type": host['inventory'].get('software_app_d', ''),
        "Group": host['inventory'].get('software_app_e', ''),
        "Assign to": host['inventory'].get('name', ''),
        "Location": host['inventory'].get('location', ''),
        "Accessories": host['inventory'].get('os_short', ''),
        "PDU IP": host['inventory'].get('hardware', ''),
        "PDU Host Port": host['inventory'].get('software_app_a', ''),
    }

    for item in host['items']:
        if item['name'] == "Linux: Active agent availability":
            host_data["Linux: Active agent availability"] = item['lastvalue']
        elif item['key_'] == "get_ip_address":
            host_data["IP"] = item['lastvalue']
        elif item['name'] == "Remote connections":
            host_data["Remote Connection"] = item['lastvalue']
        elif item['name'] == "Mev Check":
            host_data["Unit"] = item['lastvalue']
        elif item['name'] == "CI Check":
            host_data["CI Release"] = item['lastvalue']
        elif item['name'] == "BID Check":
            host_data["BID"] = item['lastvalue']
        elif item['name'] == "LP check":
            host_data["NIC"] = item['lastvalue']
        elif item['name'] == "Kernel Version Short":
            host_data["Kernel Version"] = item['lastvalue']
        elif item['name'] == "OS Name Short":
            host_data["OS Name"] = item['lastvalue']
        elif item['name'] == "Bios Version":
            host_data["Bios Version"] = item['lastvalue']
        elif item['name'] == "Motherboard Model Check":
            host_data["Motherboard"] = item['lastvalue']
        elif item['name'] == "Linux: Total memory":
            host_data["Total RAM"] = item['lastvalue']
        elif item['name'] == "f- Space utilization":
            host_data["Storage capacity"] = item['lastvalue']

    return host_data
current_time = datetime.now().strftime("%Y%m%d_%H%M")
def export_to_excel(data, filename=host_tag+"_"+current_time+".xlsx"):
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