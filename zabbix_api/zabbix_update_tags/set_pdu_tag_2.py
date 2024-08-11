from zabbix_api import ZabbixAPI
from pysnmp.hlapi import *

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "Del_Hosts"
password = "$giga"

# SNMP community and OID to get the PDU name
snmp_community = "public"
oid = "1.3.6.1.2.1.1.1.0"  # Example OID, replace with the correct one

# Path to the file containing host names
hosts_file = "hosts.txt"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

# Read host names
with open(hosts_file, "r") as file:
    host_names = [line.strip() for line in file if line.strip()]

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

def get_pdu_vendor(ip):
    """
    Get the PDU vendor based on the SNMP query.

    Args:
        ip (str): IP address of the PDU.

    Returns:
        tuple: A tuple containing the vendor name and model number.
    """
    pdu_name = snmp_get(snmp_community, ip, oid)

    if pdu_name is None:
        return "not_recognized"

    if "Aten" in pdu_name:
        return ("Aten", "11232")
    if "PX2" in pdu_name:
        return ("Raritan", "11236")
    if "EPDU" in pdu_name:
        return ("Eaton", "11301")
    
    return "not_recognized"

# Function to update host tags
def update_host_tags(host_name, requested_tags):
    """
    Updates a host with the specified tags.

    Args:
        host_name (str): Name of the host to update.
        requested_tags (list): List of dictionaries representing tags.
    """

    # Get host ID
    hosts = zapi.host.get({"filter": {"host": host_name}})
    if hosts:
        host_id = hosts[0]["hostid"]
    else:
        print("Host not found:", host_name)
        return  # Skip to the next host if not found

    # Get existing tags (optional, for reference)
    existing_tags = zapi.host.get({"hostids": host_id, "selectTags": "extend"})
    existing_tags = existing_tags[0]["tags"]
    print("Existing tags:", existing_tags)  # Uncomment to print existing tags

    # Remove "automatic" parameter from existing tags (if present)
    existing_tags = [
        {"tag": tag["tag"], "value": tag["value"]} for tag in existing_tags
    ]

    # Check for existing tags (optional)
    # for tag in requested_tags:
    #     if any(existing_tag["tag"] == tag["tag"] for existing_tag in existing_tags):
    #         print(f"Tag '{tag['tag']}' already exists for host {host_name}")
    #         continue  # Skip update if tag already exists (optional)

    # Update tag list (add requested tags)
    existing_tags.extend(requested_tags)

    # Update host with tags
    zapi.host.update(
        {
            "hostid": host_id,
            "tags": existing_tags,
        }
    )

    print(f"Successfully updated host {host_name} with tags.")

for host_name in host_names:
    # Get the host IP address
    host = zapi.host.get({"filter": {"host": host_name}, "selectInterfaces": "extend"})
    if host:
        ip_address = host[0]["interfaces"][0]["ip"]
    else:
        print("Host not found:", host_name)
        continue  # Skip to the next host if not found

    # Get PDU vendor and model
    vendor_info = get_pdu_vendor(ip_address)
    if vendor_info == "not_recognized":
        print(f"Vendor not recognized for host {host_name} with IP {ip_address}")
        continue  # Skip if vendor not recognized

    vendor_name, model_number = vendor_info

    # Create tags based on the vendor information
    requested_tags = [
        {"tag": "vendor", "value": vendor_name},
        {"tag": "model", "value": model_number},
    ]

    update_host_tags(host_name, requested_tags)
