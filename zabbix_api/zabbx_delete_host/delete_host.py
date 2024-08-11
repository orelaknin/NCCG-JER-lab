from zabbix_api import ZabbixAPI

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "Del_Hosts"
password = "$giga"

# Path to the file containing host names (one per line)
hosts_file = "hosts_delete.txt"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

# Read host names
with open(hosts_file, "r") as file:
  host_names = [line.strip() for line in file if line.strip()]

def delete_host(host_name):
  """
  Deletes a host from Zabbix server.

  Args:
      host_name (str): Name of the host to delete.
  """
  # Get host ID
  hosts = zapi.host.get({"filter": {"host": host_name}})
  if hosts:
    host_id = hosts[0]["hostid"]
  else:
    print(f"Host not found: {host_name}")
    return  # Skip to the next host if not found

  # Confirmation prompt (optional)
  # ... (same as before)

  # Delete the host (fixed line)
  zapi.host.delete({"hostid": host_id})
  print(f"Successfully deleted host: {host_name}")

for host_name in host_names:
  delete_host(host_name)
