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

def sanitize_string(value):
    if not isinstance(value, str):
        return value
    illegal_chars = {
        '\x00': '', '\x01': '', '\x02': '', '\x03': '', '\x04': '', '\x05': '',
        '\x06': '', '\x07': '', '\x08': '', '\x09': '', '\x0B': '', '\x0C': '',
        '\x0D': '', '\x0E': '', '\x0F': '', '\x10': '', '\x11': '', '\x12': '',
        '\x13': '', '\x14': '', '\x15': '', '\x16': '', '\x17': '', '\x18': '',
        '\x19': '', '\x1A': '', '\x1B': '', '\x1C': '', '\x1D': '', '\x1E': '',
        '\x1F': '',
    }
    for char, replacement in illegal_chars.items():
        value = value.replace(char, replacement)
    value = value[:32767]  # Excel cell character limit
    return value

def process_host_data(host):
    host_data = {
        "System Availability": "Up (1)" if host['status'] == '0' else "Down (2)",
        "System Name": sanitize_string(host['name']),
        "IP": sanitize_string(host['interfaces'][0]['ip'] if host['interfaces'] else ""),
        "Nuc Hostname": sanitize_string(host['inventory'].get('alias', '') if isinstance(host['inventory'], dict) else ''),
        "Link Partner": sanitize_string(host['inventory'].get('contract_number', '') if isinstance(host['inventory'], dict) else ''),
        "Host Type": sanitize_string(host['inventory'].get('software_app_d', '') if isinstance(host['inventory'], dict) else ''),
        "Group": sanitize_string(host['inventory'].get('software_app_e', '') if isinstance(host['inventory'], dict) else ''),
        "Assign to": sanitize_string(host['inventory'].get('name', '') if isinstance(host['inventory'], dict) else ''),
        "Location": sanitize_string(host['inventory'].get('location', '') if isinstance(host['inventory'], dict) else ''),
        "Accessories": sanitize_string(host['inventory'].get('os_short', '') if isinstance(host['inventory'], dict) else ''),
        "PDU IP": sanitize_string(host['inventory'].get('hardware', '') if isinstance(host['inventory'], dict) else ''),
        "PDU Host Port": sanitize_string(host['inventory'].get('software_app_a', '') if isinstance(host['inventory'], dict) else ''),
    }

    for item in host['items']:
        if item['name'] == "Linux: Active agent availability":
            host_data["Linux: Active agent availability"] = sanitize_string(item['lastvalue'])
        elif item['key_'] == "get_ip_address":
            host_data["IP"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "Remote connections":
            host_data["Remote Connection"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "Mev Check":
            host_data["Unit"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "CI Check":
            host_data["CI Release"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "BID Check":
            host_data["BID"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "LP check":
            host_data["NIC"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "Kernel Version Short":
            host_data["Kernel Version"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "OS Name Short":
            host_data["OS Name"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "Bios Version":
            host_data["Bios Version"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "Motherboard Model Check":
            host_data["Motherboard"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "MB Serial Number":
            host_data["MB serial"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "Linux: Total memory":
            host_data["Total RAM"] = sanitize_string(item['lastvalue'])
        elif item['name'] == "f- Space utilization":
            host_data["Storage capacity"] = sanitize_string(item['lastvalue'])

    return host_data

def get_top_hosts_data(zapi):
    all_hosts = []
    
    try:
        hosts = zapi.host.get({
            "output": ["hostid", "name", "status"],
            "selectInterfaces": ["ip"],
            "selectInventory": [
                "alias", "contract_number", "software", "software_app_e",
                "name", "location", "os_short", "hardware", "software_app_a", "software_app_d"
            ],
            "selectItems": ["itemid", "name", "key_", "lastvalue"],
            "sortfield": "hostid",
            "sortorder": "ASC",
        })
        if not hosts:
            print("No hosts matched")
            return None
            
        all_hosts.extend(hosts)
        print(f"Retrieved {len(all_hosts)} hosts")
        
    except Timeout:
        print("Timeout occurred. Retrying in 5 seconds...")
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

def export_to_excel(data, filename="all_hosts_" + datetime.now().strftime("%Y%m%d_%H%M") + ".xlsx"):
    if not data:
        print("No data to export")
        return
    
    try:
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"Data exported to {filename}")
    except Exception as e:
        print(f"Error exporting to Excel: {e}")

def main():
    url = "http://ladjzabbixc.jer.intel.com/zabbix/"
    username = "Del_Hosts"
    password = "$giga"
    
    zapi = zabbix_login(url, username, password)
    if zapi:
        data = get_top_hosts_data(zapi)
        if data:
            export_to_excel(data)
        zapi.logout()

if __name__ == "__main__":
    main()