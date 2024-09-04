from zabbix_api import ZabbixAPI
import argparse

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "update"
password = "$giga"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)


def update_host_groups(host_id):
    new_group_id = '22'
    
    # Get current host groups
    host_groups = zapi.hostgroup.get({"hostids": host_id, "output": ["groupid", "name"]})

    group_to_remove = next((group for group in host_groups if group["groupid"] == '22'), None)
    if not group_to_remove:
        print("Host not in maintenance")
        return
    
    # Add the new VLAN group
    updated_groups = [group for group in host_groups if group["groupid"] != '22']
    
    # Update the host's groups
    zapi.host.update({
        "hostid": host_id,
        "groups": updated_groups
    })
    print("Host removed from maintenance")

def get_host_id(host_name):    
    # Get host ID
    hosts = zapi.host.get({"filter": {"host": host_name}})
    if hosts:
        host_id = hosts[0]["hostid"]
        return host_id
    else:
        print("Host not found:", host_name)
        return
    
def main(host_name):
    host_id=get_host_id(host_name)
    update_host_groups(host_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Remove host in maintenance.')
    parser.add_argument('hostname', type=str, help='The hostname of the target machine')
    args = parser.parse_args()
    
    main(args.hostname)