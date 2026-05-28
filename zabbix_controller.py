"""
Zabbix Controller abstraction layer
Supports Zabbix-based power control system
"""

import socket
import re
from typing import Optional, Dict, Any
from datetime import datetime
import subprocess

try:
    from zabbix_api import ZabbixAPI
except ModuleNotFoundError:
    subprocess.call("python3 -m pip install zabbix_api", shell=True)
    from zabbix_api import ZabbixAPI


class Result:
    SUCCESS = 0
    ERROR = -1

def log(msg):
    """Log message with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


class ZabbixController:
    """Base class for Zabbix power controller"""

    def __init__(self, zabbix_url: str = "http://ladjzabbixc.jer.intel.com/zabbix/",
                 username: str = "power_cycle", password: str = "$giga"):
        self.zabbix_url = zabbix_url
        self.username = username
        self.password = password
        self.controller_type = "Zabbix"
        self._connectivity_tested = False
        self._current_hostname = socket.gethostname()
        self.zapi = ZabbixAPI(server=self.zabbix_url, timeout=30)
        self.zapi.login(self.username, self.password)
        # self.zapi.login(api_token="88e3f9b048396541753e269af15144be")
        self.test_connectivity()

    def power_control_command(self, hostname: str, action: str, component_type: str = "host") -> int:
        """
        Execute power control command via Zabbix API

        Args:
            hostname: Hostname to control power for
            action: Power action ('on', 'off', or 'cycle')
            component_type: Type of component ('host' for host power, 'board' for dekel)

        Returns:
            int: 0 if successful, -1 if failed
        """
        # Safety check: prevent powering off current host
        current_host = self._current_hostname.replace(".iil.intel.com", "").replace(".jer.intel.com", "")
        target_host = hostname.replace(".iil.intel.com", "").replace(".jer.intel.com", "")

        if current_host == target_host and action == "off":
            log(f"ERROR: Cannot power off current setup host {current_host}!")
            return Result.ERROR

        log(f"Zabbix Power Control: {hostname} -> {component_type.upper()} {action.upper()}")

        try:
            # Get host ID
            hostname_clean = hostname.replace(".iil.intel.com", "").replace(".jer.intel.com", "")
            host_id = self._get_host_id(hostname_clean)

            if not host_id:
                log(f"ERROR: Host {hostname_clean} not found in Zabbix")
                return Result.ERROR

            # Map action and component type to Zabbix script name
            script_name = self._get_script_name(action, component_type)
            if not script_name:
                log(f"ERROR: Invalid action/component combination: {component_type}_{action}")
                return Result.ERROR

            # Get script ID
            script_id = self._get_script_id(script_name)
            if not script_id:
                log(f"ERROR: Script {script_name} not found in Zabbix")
                return Result.ERROR

            # Execute the script
            result = self._execute_script(host_id, script_id)

            if result and result.get('response') == 'success' and 'Success' in result.get('value', ''):
                log(f"Zabbix power {action} successful for {hostname} ({component_type})")
                return 0
            else:
                log(f"Zabbix power {action} failed for {hostname} ({component_type})")
                log(f"Zabbix response: {result}")
                return Result.ERROR

        except Exception as e:
            log(f"ERROR: Zabbix power control failed: {e}")
            return Result.ERROR

    def check_power_status(self, hostname: str, component_type: str = "host") -> Optional[str]:
        """
        Check Power port status via Zabbix API

        Args:
            hostname: Hostname to check status for
            component_type: Type of component ('host' for host power, 'board' for dekel)

        Returns:
            str: Status string if successful, None if failed
        """
        log(f"Checking PDU status: {hostname} -> {component_type.upper()}")

        try:
            hostname_clean = hostname.replace(".iil.intel.com", "").replace(".jer.intel.com", "")
            host_id = self._get_host_id(hostname_clean)

            if not host_id:
                log(f"ERROR: Host {hostname_clean} not found in Zabbix")
                return None

            # Get script name for status check
            script_name = self._get_script_name("status", component_type)
            if not script_name:
                log(f"ERROR: Invalid component type for status check: {component_type}")
                return None

            script_id = self._get_script_id(script_name)
            if not script_id:
                log(f"ERROR: Script {script_name} not found in Zabbix")
                return None

            # Execute the status script
            result = self._execute_script(host_id, script_id)

            if result and result.get('response') == 'success':
                status_value = result.get('value', '')
                log(f"Power status check successful for {hostname} ({component_type}): {status_value}")
                return status_value
            else:
                log(f"Power status check failed for {hostname} ({component_type})")
                log(f"Zabbix response: {result}")
                return None

        except Exception as e:
            log(f"ERROR: PDU status check failed: {e}")
            return None

    def check_host_availability(self, hostname: str) -> Optional[bool]:
        """
        Check host availability status in Zabbix

        Args:
            hostname: Hostname to check availability for

        Returns:
            bool: True if available, False if unavailable, None if unknown/error
        """
        hostname_clean = hostname.replace(".iil.intel.com", "").replace(".jer.intel.com", "")
        log(f"Checking Zabbix host availability: {hostname_clean}")

        try:
            # Get host information with active agent availability
            hosts = self.zapi.host.get({
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
                log(f"Host {hostname_clean} active agent is available in Zabbix")
                return True
            elif active_available == 2:
                log(f"Host {hostname_clean} active agent is unavailable in Zabbix")
                return False
            else:
                log(f"Host {hostname_clean} active agent availability is unknown in Zabbix (status: {active_available})")
                return None

        except Exception as e:
            log(f"ERROR: Failed to check Zabbix host availability for {hostname_clean}: {e}")
            import traceback
            log(f"DEBUG: {traceback.format_exc()}")
            return None

    def get_host_ip_address(self, hostname: str) -> Optional[str]:
        """
        Get the IP address for a host by executing Zabbix script

        Args:
            hostname: Hostname to get IP address for

        Returns:
            str: IP address if script execution successful, None if failed
        """
        hostname_clean = hostname.replace(".iil.intel.com", "").replace(".jer.intel.com", "")
        log(f"Getting IP address for host: {hostname_clean}")

        try:
            # Get host ID
            host_id = self._get_host_id(hostname_clean)
            if not host_id:
                log(f"ERROR: Host {hostname_clean} not found in Zabbix")
                return None

            # Get the script name for IP address retrieval
            script_name = "get ip address"
            script_id = self._get_script_id(script_name)
            if not script_id:
                log(f"ERROR: Script {script_name} not found in Zabbix")
                return None

            # Execute the script
            result = self._execute_script(host_id, script_id)

            if result and result.get('response') == 'success':
                ip_address = result.get('value', '').strip()
                if ip_address:
                    log(f"Retrieved IP address for {hostname_clean}: {ip_address}")
                    return ip_address
                else:
                    log(f"WARNING: Script executed successfully but returned empty IP for {hostname_clean}")
                    return None
            else:
                log(f"Failed to get IP address for {hostname_clean}")
                log(f"Zabbix response: {result}")
                return None

        except Exception as e:
            log(f"ERROR: Failed to get IP address for {hostname_clean}: {e}")
            return None

    def is_board_port_configured(self, hostname: str) -> bool:
        """
        Check if board PDU port is configured for a host in Zabbix inventory

        Args:
            hostname: Hostname to check board PDU port configuration for

        Returns:
            bool: True if board PDU port is configured, False otherwise
        """
        hostname_clean = hostname.replace(".iil.intel.com", "").replace(".jer.intel.com", "")
        log(f"Checking if board PDU port is configured for host: {hostname_clean}")

        try:
            hosts = self.zapi.host.get({
                "output": ["hostid", "name"],
                "selectInventory": ["type_full"],
                "filter": {"name": hostname_clean}
            })
            
            if not hosts:
                log(f"No host found with hostname: {hostname_clean}")
                return False
            
            host = hosts[0]
            type_full = host.get('inventory', {}).get('type_full', '')
            
            if not type_full:
                log(f"No board PDU port data found for hostname: {hostname_clean}")
                return False
            
            # Extract the first number from the type_full field
            match = re.search(r'\d+', type_full)
            if match:
                port_number = int(match.group(0))
                log(f"Board PDU port configured for {hostname_clean}: {port_number}")
                return True
            else:
                log(f"No number found in board PDU port field: {type_full}")
                return False
                
        except Exception as e:
            log(f"Error querying Zabbix for hostname {hostname_clean}: {e}")
            return False

    def _get_host_id(self, hostname: str) -> Optional[str]:
        """Get host ID from Zabbix"""
        try:
            hosts = self.zapi.host.get({"filter": {"host": hostname}})
            if hosts:
                return hosts[0]["hostid"]
            return None
        except Exception as e:
            log(f"Error getting host ID for {hostname}: {e}")
            return None

    def _get_script_id(self, script_name: str) -> Optional[str]:
        """Get script ID from Zabbix"""
        try:
            scripts = self.zapi.script.get({"output": "extend", "filter": {"name": script_name}})
            if scripts:
                return scripts[0]["scriptid"]
            return None
        except Exception as e:
            log(f"Error getting script ID for {script_name}: {e}")
            return None

    def _execute_script(self, host_id: str, script_id: str) -> Optional[Dict]:
        """Execute script on host via Zabbix"""
        try:
            result = self.zapi.script.execute({
                "scriptid": script_id,
                "hostid": host_id
            })
            return result
        except Exception as e:
            log(f"Script execution error: {e}")
            return None

    def _get_script_name(self, action: str, component_type: str) -> Optional[str]:
        """Map action and component type to Zabbix script name"""
        action_map = {
            ("host", "on"): "PDU host power on",
            ("host", "off"): "PDU host power off",
            ("host", "cycle"): "PDU host power cycle",
            ("host", "status"): "Power Host status",
            ("board", "on"): "PDU Board power on",
            ("board", "off"): "PDU Board power off",
            ("board", "cycle"): "PDU Board power cycle",
            ("board", "status"): "Power Board status"
        }
        return action_map.get((component_type, action))

    def test_connectivity(self) -> bool:
        """Test connectivity to Zabbix server"""
        if self._connectivity_tested:
            return True

        log(f"Testing Zabbix connectivity to {self.zabbix_url}...")

        try:
            self.zapi.login(self.username, self.password)
            log(f"Zabbix server {self.zabbix_url} is reachable")
            self._connectivity_tested = True
            return True
        except Exception as e:
            log(f"Zabbix server {self.zabbix_url} is not reachable: {e}")
            return Result.ERROR

    def get_controller_info(self) -> Dict[str, Any]:
        """Get controller information"""
        return {
            'url': self.zabbix_url,
            'type': self.controller_type,
            'connectivity_tested': self._connectivity_tested,
            'current_host': self._current_hostname
        }
