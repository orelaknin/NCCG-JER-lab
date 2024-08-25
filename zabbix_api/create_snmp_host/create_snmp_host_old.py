from zabbix_api import ZabbixAPI
import socket

# Zabbix server details
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"
username = "create"
password = "$giga"
snmp_community = "NCCGRR"
group_id = "34"  # Adjust this to the appropriate group ID
template_id = "10563"
ips_file = "ips.txt"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)


# Read IPs from the file
with open(ips_file, "r") as file:
    ip_list = [line.strip() for line in file if line.strip()]

def get_hostname(ip_address):
    """
    Resolves the hostname for a given IP address.

    Args:
        ip_address (str): The IP address to resolve.

    Returns:
        str: The resolved hostname or the IP address if the hostname is not found.
    """
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except socket.herror:
        return ip_address  # Use IP as the hostname if DNS name not found

def ping(ip):
    """
    Pings the given IP address to check if it is reachable.

    Args:
        ip (str): The IP address to ping.

    Returns:
        bool: True if the IP is reachable, False otherwise.
    """
    try:
        socket.gethostbyname(ip)
        return True
    except socket.error:
        return False

def create_host(ip):
    """
    Creates a host in Zabbix with an SNMP v1 interface and updates its name by fetching the DNS name.

    Args:
        ip (str): IP address of the host.
    """
    # Ping the IP to check if it's reachable
    if not ping(ip):
        print(f"Host not reachable: {ip}")
        return  # Skip to the next IP if not reachable

    # Get DNS name
    dns_name = get_hostname(ip)

    # Create host in Zabbix
    try:
        zapi.host.create({
            "host": dns_name.split('.')[0],
            "interfaces": [
                {
                    "type": 2,  # SNMP interface
                    "main": 1,
                    "useip": 1,
                    "ip": ip,
                    "dns": "",
                    "port": "161",
                    "details": {
                        "version": 1,
                        "community": snmp_community
                    }
                }
            ],
            "groups": [
                {
                    "groupid": group_id
                }
            ],
            "templates": [
                {
                    "templateid": template_id 
                },
                {
                    "templateid": "11232" 
                }
            ]
        })
        print(f"Successfully created host: {dns_name}")
    except Exception as e:
        print(f"Error creating host for IP {ip}: {e}")

for ip in ip_list:
    create_host(ip)
