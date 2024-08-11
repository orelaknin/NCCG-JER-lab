from zabbix_api import ZabbixAPI
import socket
from pysnmp.hlapi import *

# Zabbix server details
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"
username = "Del_Hosts"
password = "$giga"
snmp_community = "NCCGRR"
group_id = "34"  # Adjust this to the appropriate group ID
ips_file = "ips.txt"
oid = "1.3.6.1.2.1.1.1.0"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

# Read IPs from the file
with open(ips_file, "r") as file:
    ip_list = [line.strip() for line in file if line.strip()]

# SNMP API, for getting PDUs vendor
def snmp_get(community, ip, oid):
    """
    Perform an SNMP GET operation.

    Args:
        community (str): SNMP community string.
        ip (str): IP address of the device.
        oid (str): OID to query.

    Returns:
        str: The value returned by the SNMP GET operation.
    """
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=0),  # Using SNMPv1
        UdpTransportTarget((ip, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )

    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

    if errorIndication:
        print(f"SNMP error: {errorIndication}")
        return None
    elif errorStatus:
        print(f"SNMP error: {errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}")
        return None
    else:
        for varBind in varBinds:
            return varBind[1].prettyPrint()

# Get the hostname of the IP
def get_hostname(ip_address):
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except socket.herror:
        return ip_address  # Use IP as the hostname if DNS name not found

# Ping the IP to check if it's reachable
def ping(ip):
    try:
        socket.gethostbyname(ip)
        return True
    except socket.error:
        return False

# Get the PDU vendor and corresponding template ID
def get_pdu_vendor(ip):
    pdu_name = snmp_get(snmp_community, ip, oid)
    
    if pdu_name is None:
        return None

    if "Aten" in pdu_name:
        return ("Aten", "11232")
    if "PX2" in pdu_name:
        return ("Raritan", "11236")
    if "EPDU" in pdu_name:
        return ("Eaton", "11301")
    
    return "not_recognized"

# Create a host in Zabbix
def create_host(dns_name, ip, pdu_name_template):
    pdu_name, template_id = pdu_name_template
    dns_name = dns_name if dns_name == ip else dns_name.split(".")[0]

    # Check if the host already exists
    host_info = zapi.host.get({
        "filter": {"host": dns_name}
    })

    if host_info:
        print(f"Host already exists: {dns_name}")
        return None
    
    # Create the host
    try:
        zapi.host.create({
            "host": dns_name,
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
                    "templateid": "10563"  # Adjust if needed
                }
            ]
        })
        print(f"Successfully created host: {dns_name}")
    except Exception as e:
        print(f"Error creating host for IP {ip}: {e}")

# Process each IP
for ip in ip_list:
    if not ping(ip):
        print(f"Host not reachable: {ip}")
        continue
    
    dns_name = get_hostname(ip)
    pdu_name_template = get_pdu_vendor(ip)

    if isinstance(pdu_name_template, str):
        print(f"Unrecognized PDU for IP {ip}")
        continue

    create_host(dns_name, ip, pdu_name_template)
