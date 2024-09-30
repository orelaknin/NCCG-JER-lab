from zabbix_api import ZabbixAPI
import time
from requests.exceptions import Timeout, RequestException

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "update"
password = "$giga"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)


def get_host_model(zapi, ip_address):
    try:
        hosts = zapi.host.get({
            "output": ["hostid", "name"],
            "selectInterfaces": ["ip"],
            "selectItems": ["itemid", "name", "key_", "lastvalue"],
            "filter": {
                "ip": ip_address
            }
        })
        
        if not hosts:
            print(f"No host found with IP address: {ip_address}")
            return None
        
        host = hosts[0]
        model = None
        
        for item in host['items']:
            if item['name'] == "Generic SNMP: System description":
                model = item['lastvalue']
                break
        
        if model:
            return f"Model for IP {ip_address}: {model}"
        else:
            return f"No model information found for IP {ip_address}"
        
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

def main():
    
    ip_address = input("Enter the IP address to check: ")
    
    if zapi:
        result = get_host_model(zapi, ip_address)
        if result:
            print(result)
        zapi.logout()

if __name__ == "__main__":
    main()