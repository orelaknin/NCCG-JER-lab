from zabbix_api import ZabbixAPI
import pandas as pd
import time
from requests.exceptions import Timeout, RequestException
from datetime import datetime
import shutil
import os
import re

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
                "name", "location", "os_short", "hardware", "software_app_a", "software_app_d"
            ],
            "selectItems": ["itemid", "name", "key_", "lastvalue"],
            "sortfield": "hostid",
            "sortorder": "ASC",
            "templateids": ["10896"],
        })
        if not hosts:
            print("No hosts matched")
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
        lastvalue = item['lastvalue']
        if item['name'] == "Linux: Active agent availability":
            host_data["Linux: Active agent availability"] = lastvalue
        elif item['key_'] == "get_ip_address":
            host_data["IP"] = lastvalue
        elif item['name'] == "Remote connections":
            host_data["Remote Connection"] = lastvalue
        elif item['name'] == "Mev Check":
            host_data["Unit"] = lastvalue
        elif item['name'] == "CI Check":
            host_data["CI Release"] = lastvalue
        elif item['name'] == "BID Check":
            host_data["BID"] = lastvalue
        elif item['name'] == "LP check":
            host_data["NIC"] = lastvalue
        elif item['name'] == "Kernel Version Short":
            host_data["Kernel Version"] = lastvalue
        elif item['name'] == "OS Name Short":
            host_data["OS Name"] = lastvalue
        elif item['name'] == "Bios Version":
            host_data["Bios Version"] = lastvalue
        elif item['name'] == "Motherboard Model Check":
            host_data["Motherboard"] = lastvalue
        elif item['name'] == "Linux: Total memory":
            host_data["Total RAM"] = lastvalue
        elif item['name'] == "f- Space utilization":
            host_data["Storage capacity"] = lastvalue

    # Sanitize all values in host_data
    sanitized_host_data = {}
    for key, value in host_data.items():
        sanitized_value = clean_string(value)
        sanitized_host_data[key] = sanitized_value
        if value != sanitized_value:
            print(f"Sanitized {key}: '{value}' -> '{sanitized_value}'")

    return sanitized_host_data

def clean_string(value):
    """Remove or replace problematic characters/strings for Excel."""
    if not isinstance(value, str):
        return value  # Leave non-strings (e.g., numbers) unchanged
    # Remove control characters
    value = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', value)
    # Handle specific problematic string
    if "Sudo is disabled" in value:
        return "Sudo disabled (check settings)"
    return value

def get_or_create_daily_folder(base_path):
    today = datetime.now().strftime("%Y-%m-%d")
    daily_folder = os.path.join(base_path, today)
    
    if not os.path.exists(daily_folder):
        os.makedirs(daily_folder)
        print(f"Created folder for today: {daily_folder}")
    else:
        print(f"Using existing folder for today: {daily_folder}")
    
    return daily_folder

def export_to_excel(data, base_folder):
    if not data:
        print("No data to export")
        return None
    
    daily_folder = get_or_create_daily_folder(base_folder)
    current_time = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"zab_{current_time}.xlsx"
    full_path = os.path.join(daily_folder, filename)
    
    df = pd.DataFrame(data)
    try:
        df.to_excel(full_path, index=False)
        print(f"Data exported to {full_path}")
    except Exception as e:
        print(f"Failed to export to Excel: {e}")
        # Fallback to CSV for debugging
        csv_path = full_path.replace('.xlsx', '.csv')
        df.to_csv(csv_path, index=False)
        print(f"Saved raw data to CSV: {csv_path}")
    return full_path

def main():
    url = "http://ladjzabbixc.jer.intel.com/zabbix/"
    username = "backup"
    password = "$giga"
    
    # Hardcoded fileshare path (replace with your actual path)
    fileshare_base_path = r"\\ladjitfstech.ger.corp.intel.com\Zabbix Excels"
    
    zapi = zabbix_login(url, username, password)
    if zapi:
        data = get_top_hosts_data(zapi)
        if data:
            export_to_excel(data, fileshare_base_path)
        zapi.logout()

if __name__ == "__main__":
    main()