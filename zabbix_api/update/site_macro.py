#!/usr/bin/env python3
from zabbix_api import ZabbixAPI
from typing import Optional

ZABBIX_URL = "http://ladjzabbixc.jer.intel.com/zabbix/"
ZABBIX_USER = "Del_Hosts"
ZABBIX_PASS = "$giga"

def log(message):
    """Simple logging function"""
    print(message)

# --------------------------
#  HELPER FUNCTIONS
# --------------------------
def get_group_id(zapi, group_name: str) -> Optional[str]:
    """Get group ID by group name"""
    groups = zapi.hostgroup.get({
        "output": ["groupid"],
        "filter": {"name": group_name}
    })
    return groups[0]["groupid"] if groups else None

def get_host_id(zapi, hostname: str) -> Optional[str]:
    """Get host ID by hostname"""
    hostname_clean = hostname.replace(".iil.intel.com", "").replace(".jer.intel.com", "")
    hosts = zapi.host.get({
        "output": ["hostid"],
        "filter": {"host": hostname_clean}
    })
    return hosts[0]["hostid"] if hosts else None

def get_script_id(zapi, script_name: str) -> Optional[str]:
    """Get script ID by script name"""
    scripts = zapi.script.get({
        "output": ["scriptid"],
        "filter": {"name": script_name}
    })
    return scripts[0]["scriptid"] if scripts else None

def execute_script(zapi, host_id: str, script_id: str) -> dict:
    """Execute script on host"""
    return zapi.script.execute({
        "scriptid": script_id,
        "hostid": host_id
    })

def check_host_availability(zapi, hostname: str) -> Optional[bool]:
    """
    Check host availability status in Zabbix

    Args:
        zapi: Zabbix API instance
        hostname: Hostname to check availability for

    Returns:
        bool: True if available, False if unavailable, None if unknown/error
    """
    hostname_clean = hostname.replace(".iil.intel.com", "").replace(".jer.intel.com", "")
    log(f"Checking Zabbix host availability: {hostname_clean}")

    try:
        # Get host information with active agent availability
        hosts = zapi.host.get({
            "output": ["hostid", "host", "name", "status", "active_available"],
            "filter": {
                "host": [hostname_clean]
            }
        })

        if not hosts:
            log(f"ERROR: Host {hostname_clean} not found in Zabbix")
            return None

        host_info = hosts[0]

        # Check host status (0 = monitored, 1 = not monitored)
        host_status = int(host_info.get('status', 1))

        if host_status != 0:
            log(f"Host {hostname_clean} is not monitored in Zabbix (status: {host_status})")
            return None

        # Check active agent availability using the active_available field
        active_available = int(host_info.get('active_available', 0))

        # Interpret active agent availability status:
        # 0 = unknown, 1 = available, 2 = unavailable
        if active_available == 1:
            log(f"✓ Host {hostname_clean} active agent is available in Zabbix")
            return True
        elif active_available == 2:
            log(f"✗ Host {hostname_clean} active agent is unavailable in Zabbix")
            return False
        else:
            log(f"⚠ Host {hostname_clean} active agent availability is unknown in Zabbix (status: {active_available})")
            return None

    except Exception as e:
        log(f"ERROR: Failed to check Zabbix host availability for {hostname_clean}: {e}")
        import traceback
        log(f"DEBUG: {traceback.format_exc()}")
        return None

def get_host_ip_address(zapi, hostname: str) -> Optional[str]:
    """
    Get the IP address for a host by executing Zabbix script

    Args:
        zapi: Zabbix API instance
        hostname: Hostname to get IP address for

    Returns:
        str: IP address if script execution successful, None if failed
    """
    hostname_clean = hostname.replace(".iil.intel.com", "").replace(".jer.intel.com", "")
    log(f"Getting IP address for host: {hostname_clean}")

    try:
        # Get host ID
        host_id = get_host_id(zapi, hostname_clean)
        if not host_id:
            log(f"ERROR: Host {hostname_clean} not found in Zabbix")
            return None

        # Get the script name for IP address retrieval
        script_name = "get ip address"
        script_id = get_script_id(zapi, script_name)
        if not script_id:
            log(f"ERROR: Script {script_name} not found in Zabbix")
            return None

        # Execute the script
        result = execute_script(zapi, host_id, script_id)

        if result and result.get('response') == 'success':
            ip_address = result.get('value', '').strip()
            if ip_address:
                log(f"✓ Retrieved IP address for {hostname_clean}: {ip_address}")
                return ip_address
            else:
                log(f"WARNING: Script executed successfully but returned empty IP for {hostname_clean}")
                return None
        else:
            log(f"✗ Failed to get IP address for {hostname_clean}")
            log(f"Zabbix response: {result}")
            return None

    except Exception as e:
        log(f"ERROR: Failed to get IP address for {hostname_clean}: {e}")
        return None

# --------------------------
#  FUNCTION: determine site
# --------------------------
def detect_site(ip):
    if ip.startswith("10.12."):
        return "jer"
    else:
        return "iil"

# --------------------------
#  MAIN
# --------------------------
def main():
    zapi = ZabbixAPI(server=ZABBIX_URL)
    zapi.login(ZABBIX_USER, ZABBIX_PASS)

    print("Connected to Zabbix.")

    # Get the group ID for "Linux servers"
    group_name = "Linux servers"
    group_id = get_group_id(zapi, group_name)
    if not group_id:
        print(f"ERROR: Group '{group_name}' not found in Zabbix")
        return

    print(f"Found group '{group_name}' with ID: {group_id}")

    # Get hosts only from the "Linux servers" group
    hosts = zapi.host.get({
        "output": ["hostid", "host"],
        "groupids": [group_id]
    })

    for host in hosts:
        hostid = host["hostid"]
        hostname = host["host"]

        # ------------------------
        # Check host availability first
        # ------------------------
        availability = check_host_availability(zapi, hostname)
        
        if availability is None:
            print(f"[SKIP] {hostname}: Host not found or not monitored")
            continue
        elif availability is False:
            print(f"[SKIP] {hostname}: Host agent is unavailable")
            continue
        
        print(f"[INFO] {hostname}: Host is available, proceeding with IP retrieval")

        # ------------------------
        # Get the IP address using script execution
        # ------------------------
        ip = get_host_ip_address(zapi, hostname)

        if not ip:
            print(f"[SKIP] {hostname}: Could not retrieve IP address")
            continue

        # Determine site
        site = detect_site(ip)

        print(f"[INFO] Host: {hostname}, IP(from script): {ip}, Site: {site}")

        # ------------------------
        # Update host macro {$SITE}
        # ------------------------
        host_data = zapi.host.get({
            "hostids": hostid,
            "selectMacros": ["macro", "value"]
        })

        macros = host_data[0].get("macros", [])
        found = False

        for m in macros:
            if m["macro"] == "{$SITE}":
                found = True
                if m["value"] != site:
                    print(f"  -> Updating {{$SITE}} from {m['value']} to {site}")
                    m["value"] = site
                break

        if not found:
            print(f"  -> Creating {{$SITE}} = {site}")
            macros.append({"macro": "{$SITE}", "value": site})

        # Send update
        zapi.host.update({
            "hostid": hostid,
            "macros": macros
        })

    print("\nDone. All hosts updated based on script execution.")

if __name__ == "__main__":
    main()
