from zabbix_api import ZabbixAPI

# Define the Zabbix server URL and login credentials
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"
username = "Del_Hosts"
password = "$giga"

try:
    # Connect to the Zabbix API
    zapi = ZabbixAPI(server=server_url)
    zapi.login(username, password)
    
    # Get all scripts
    scripts = zapi.script.get({"output": "extend"})
    print("API Response:", scripts)  # Print the entire response for debugging

finally:
    # Logout from the Zabbix API
    zapi.logout()
