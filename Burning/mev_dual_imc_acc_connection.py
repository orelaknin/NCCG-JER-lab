#!/usr/bin/env python3
"""
IPU Generic Multi-Interface Access Script
Power-cycle ready script that automatically sets up multi-IPU access
Supports 1-4 ethernet interfaces with command-line configuration
Supports MEV and MMG devices (IPU family)
Includes interface initialization and MAC address discovery
"""

import subprocess
import sys
import time
import os
import re
import argparse

# IMC to ACC connection configuration
IMC_TO_ACC_ETH_INTERFACE = "eth2"  # Internal ethernet port on IMC for ACC connection
ACC_NETWORK_IP = "192.168.96.1/24"
ACC_TARGET_IP = "192.168.96.2"

class InterfaceConfig:
    """Configuration for network interfaces"""
    def __init__(self, enabled_interfaces):
        self.interfaces = []
        self.interface_macs = {}
        self.interface_ips = {}

        # Build interface configuration
        for i, interface in enumerate(enabled_interfaces):
            config = {
                'name': interface,
                'host_ip': f"100.0.{i}.1/24",
                'target_ip': f"100.0.{i}.100",
                'index': i
            }
            self.interfaces.append(config)

    def get_interface_by_name(self, name):
        """Get interface config by name"""
        for interface in self.interfaces:
            if interface['name'] == name:
                return interface
        return None

    def get_primary_interface(self):
        """Get the first interface (primary)"""
        return self.interfaces[0] if self.interfaces else None

    def get_interface_count(self):
        """Get number of configured interfaces"""
        return len(self.interfaces)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='IPU Generic Multi-Interface Access Script',
        epilog='Example: %(prog)s --eth1 --eth2 --eth3'
    )

    parser.add_argument('--eth1', action='store_true',
                       help='Enable eth1 interface')
    parser.add_argument('--eth2', action='store_true',
                       help='Enable eth2 interface')
    parser.add_argument('--eth3', action='store_true',
                       help='Enable eth3 interface')
    parser.add_argument('--eth4', action='store_true',
                       help='Enable eth4 interface')

    args = parser.parse_args()

    # Build list of enabled interfaces
    enabled_interfaces = []
    if args.eth1:
        enabled_interfaces.append('eth1')
    if args.eth2:
        enabled_interfaces.append('eth2')
    if args.eth3:
        enabled_interfaces.append('eth3')
    if args.eth4:
        enabled_interfaces.append('eth4')

    if not enabled_interfaces:
        print(f"{Colors.RED}Error: At least one interface must be specified (--eth1, --eth2, --eth3, or --eth4){Colors.NC}")
        parser.print_help()
        sys.exit(1)

    return enabled_interfaces

class Colors:
    RED = '\033[1;31m'
    GREEN = '\033[1;32m'
    BLUE = '\033[1;34m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color

def print_colored(message: str, color: str) -> None:
    """Print colored message to console"""
    print(f"{color}{message}{Colors.NC}")

def run_command(command: str) -> tuple[bool, str]:
    """Execute shell command and return success status and output"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        # For commands like arping, combine stdout and stderr
        output = result.stdout.strip() + " " + result.stderr.strip()
        return result.returncode == 0, output.strip()
    except Exception as e:
        return False, str(e)

def set_interface_state(interface: str, state: str) -> tuple[bool, str]:
    """Set interface up or down"""
    return run_command(f"sudo ip link set {interface} {state}")

def flush_interface_addresses(interface: str) -> tuple[bool, str]:
    """Flush all IP addresses from an interface"""
    return run_command(f"sudo ip addr flush dev {interface}")

def add_interface_ip(interface: str, ip_address: str) -> tuple[bool, str]:
    """Add IP address to interface"""
    return run_command(f"sudo ip addr add {ip_address} dev {interface}")

def add_static_neighbor(ip: str, mac: str, interface: str) -> tuple[bool, str]:
    """Add static neighbor entry"""
    return run_command(f"sudo ip neigh add {ip} lladdr {mac} dev {interface} nud permanent")

def add_route(destination: str, interface: str, source_ip: str = None) -> tuple[bool, str]:
    """Add route to destination via interface"""
    src_part = f" src {source_ip}" if source_ip else ""
    return run_command(f"sudo ip route add {destination} dev {interface}{src_part}")

def ping_host(host: str, count: int = 2, timeout: int = 3) -> tuple[bool, str]:
    """Ping a host with specified count and timeout"""
    return run_command(f"ping -c {count} -W {timeout} {host}")

def ssh_command(host: str, command: str, timeout: int = 10) -> tuple[bool, str]:
    """Execute SSH command on remote host"""
    return run_command(f"timeout {timeout} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@{host} '{command}' 2>/dev/null")

def arping_discover(interface: str, target_ip: str, count: int = 3, timeout: int = 5) -> tuple[bool, str]:
    """Discover MAC address using arping"""
    return run_command(f"arping -I {interface} -c {count} -w {timeout} {target_ip}")

def setup_imc_to_acc_connection(imc_ip: str, imc_name: str) -> bool:
    """Setup ACC connection via IMC using internal ethernet port"""
    print_colored(f"Setting up {imc_name} to ACC connection...", Colors.BLUE)

    acc_commands = [
        "modprobe icc_net",
        f"ip link set {IMC_TO_ACC_ETH_INTERFACE} up",
        "ip link set lo up",
        f"ip addr add {ACC_NETWORK_IP} brd + dev {IMC_TO_ACC_ETH_INTERFACE}"
    ]

    for cmd in acc_commands:
        success, output = ssh_command(imc_ip, cmd, 10)
        if success or "File exists" in str(output) or "Cannot assign requested address" in str(output):
            print_colored(f"? {imc_name}: {cmd}", Colors.GREEN)
        else:
            print_colored(f"?? {imc_name}: {cmd} - {output}", Colors.YELLOW)

    return True

def test_acc_connection(imc_ip: str, imc_name: str) -> bool:
    """Test ACC connection via IMC"""
    time.sleep(3)
    success, whoami = ssh_command(imc_ip, f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@{ACC_TARGET_IP} "whoami"', 10)
    if success and "root" in whoami:
        print_colored(f"? {imc_name} to ACC connection verified", Colors.GREEN)
        return True
    else:
        print_colored(f"? {imc_name} to ACC connection failed", Colors.RED)
        return False

def initialize_interfaces(config: InterfaceConfig) -> bool:
    """Step 0: Initialize network interfaces and test basic connectivity"""
    print_colored("\n=== Step 0: Interface Initialization ===", Colors.YELLOW)
    print_colored("1. Bringing up network interfaces...", Colors.BLUE)

    # Bring up all configured interfaces
    for interface in config.interfaces:
        set_interface_state(interface['name'], "up")

    # Give interfaces time to come up
    time.sleep(3)

    # Clear any existing configuration
    for interface in config.interfaces:
        flush_interface_addresses(interface['name'])
    run_command("sudo ip neigh flush all")

    # Basic configuration to test connectivity - ALL interfaces use 100.0.0.x subnet initially
    for i, interface in enumerate(config.interfaces):
        # During initialization, use 100.0.0.x subnet for all interfaces
        init_host_ip = f"100.0.0.{i+1}/24"
        add_interface_ip(interface['name'], init_host_ip)

    print_colored("2. Testing basic IPU connectivity...", Colors.BLUE)

    # Test connectivity with the common target IP (100.0.0.100)
    success, _ = ping_host("100.0.0.100")
    if not success:
        print_colored("? No IPU responding. Check physical connections and power.", Colors.RED)
        return False

    print_colored("? At least one IPU is responding", Colors.GREEN)
    return True

def discover_ipu_mac_addresses(config: InterfaceConfig) -> dict:
    """Step 1: Discover MAC addresses of all IPU devices"""
    print_colored("\n3. Discovering MAC addresses...", Colors.BLUE)
    discovered_macs = {}

    # Discover MAC for each interface - all should try to reach 100.0.0.100 initially
    for i, interface in enumerate(config.interfaces):
        print_colored(f"   Discovering IPU{i+1} MAC via {interface['name']}...", Colors.BLUE)

        # Disable other interfaces to isolate discovery
        for other_interface in config.interfaces:
            if other_interface['name'] != interface['name']:
                set_interface_state(other_interface['name'], "down")

        # Ensure current interface is up and configured
        set_interface_state(interface['name'], "up")
        run_command("sudo ip neigh flush all")
        time.sleep(3)  # Give interface more time to stabilize

        # Configure interface for discovery - use 100.0.0.x subnet initially for all
        flush_interface_addresses(interface['name'])
        discovery_host_ip = f"100.0.0.{i+1}/24"  # eth1=100.0.0.1, eth2=100.0.0.2, etc.
        discovery_target_ip = "100.0.0.100"      # All try to reach the same target initially

        add_interface_ip(interface['name'], discovery_host_ip)
        time.sleep(3)  # Give IP configuration time to settle

        # Check if interface is actually up and has connectivity
        success, link_output = run_command(f"ip link show {interface['name']}")
        if success and "UP" in link_output:
            print_colored(f"   Interface {interface['name']} is UP", Colors.GREEN)
        else:
            print_colored(f"   Warning: Interface {interface['name']} may not be properly UP", Colors.YELLOW)

        # Test basic connectivity first
        print_colored(f"   Testing ping to {discovery_target_ip} via {interface['name']}...", Colors.BLUE)
        ping_success, ping_output = ping_host(discovery_target_ip, 2, 3)
        if ping_success:
            print_colored(f"   Ping successful, proceeding with ARP discovery", Colors.GREEN)
        else:
            print_colored(f"   Ping failed: {ping_output}", Colors.YELLOW)
            print_colored(f"   Attempting ARP discovery anyway...", Colors.BLUE)

        success_arp, arp_output = arping_discover(interface['name'], discovery_target_ip)
        if success_arp or arp_output:  # Accept if we got any output, even with non-zero exit
            mac_match = re.search(r'([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})', arp_output)
            if mac_match:
                mac_address = mac_match.group(1).lower()
                discovered_macs[interface['name']] = mac_address
                config.interface_macs[interface['name']] = mac_address
                print_colored(f"? IPU{i+1} MAC discovered: {mac_address}", Colors.GREEN)
            else:
                print_colored(f"? Could not discover IPU{i+1} MAC address from ARP output: {arp_output}", Colors.RED)
                # Try to get MAC from ARP table as fallback
                success, arp_table = run_command(f"ip neigh show {discovery_target_ip}")
                if success and arp_table:
                    mac_match = re.search(r'([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})', arp_table)
                    if mac_match:
                        mac_address = mac_match.group(1).lower()
                        discovered_macs[interface['name']] = mac_address
                        config.interface_macs[interface['name']] = mac_address
                        print_colored(f"? IPU{i+1} MAC found in ARP table: {mac_address}", Colors.GREEN)
                        continue
                return None
        else:
            print_colored(f"? Failed to ARP IPU{i+1} via {interface['name']}", Colors.RED)
            print_colored(f"   ARP output: {arp_output}", Colors.YELLOW)

            # Additional debugging
            success, route_info = run_command(f"ip route show dev {interface['name']}")
            print_colored(f"   Routes for {interface['name']}: {route_info}", Colors.BLUE)

            success, addr_info = run_command(f"ip addr show {interface['name']}")
            print_colored(f"   Address info for {interface['name']}: {addr_info.split()[:10]}", Colors.BLUE)

            return None

    # Verify we have unique MAC addresses for each interface
    mac_values = list(discovered_macs.values())
    if len(set(mac_values)) != len(mac_values):
        print_colored("? Some interfaces show same MAC - devices may be connected incorrectly", Colors.RED)
        for name, mac in discovered_macs.items():
            print_colored(f"   {name}: {mac}", Colors.RED)
        return None

    print_colored(f"? {len(discovered_macs)} different IPU devices confirmed:", Colors.GREEN)
    for i, (name, mac) in enumerate(discovered_macs.items()):
        print_colored(f"   IPU{i+1} ({name}): {mac}", Colors.GREEN)

    return discovered_macs

def configure_ipu_secondary_ips(config: InterfaceConfig) -> bool:
    """Step 2: Configure IPU devices with secondary IP addresses"""
    print_colored("\n=== Step 1: Configure IPU Secondary IPs ===", Colors.YELLOW)

    if config.get_interface_count() <= 1:
        print_colored("Only one interface configured, skipping secondary IP configuration", Colors.BLUE)
        return True

    # For interfaces beyond the first one, we need to configure them to use unique IPs
    # IPU1 stays at 100.0.0.100, IPU2 gets 100.0.1.100, etc.
    for i, interface in enumerate(config.interfaces[1:], 1):
        print_colored(f"\n{i}. Configuring IPU{i+1} to use IP {interface['target_ip']}...", Colors.BLUE)

        # Isolate this interface
        for other_interface in config.interfaces:
            if other_interface['name'] != interface['name']:
                set_interface_state(other_interface['name'], "down")

        set_interface_state(interface['name'], "up")
        flush_interface_addresses(interface['name'])

        # Initially configure with 100.0.0.x to reach the IPU at 100.0.0.100
        temp_host_ip = f"100.0.0.{i+1}/24"
        add_interface_ip(interface['name'], temp_host_ip)
        run_command("sudo ip neigh flush all")

        # Add static ARP for this IPU using its discovered MAC and original IP (100.0.0.100)
        ipu_mac = config.interface_macs[interface['name']]
        add_static_neighbor("100.0.0.100", ipu_mac, interface['name'])

        time.sleep(2)

        # Test connectivity with the original discovery IP (100.0.0.100)
        success, _ = ping_host("100.0.0.100")
        if not success:
            print_colored(f"? Cannot reach IPU{i+1} at 100.0.0.100 for configuration", Colors.RED)
            return False

        print_colored(f"? IPU{i+1} accessible at 100.0.0.100 for configuration", Colors.GREEN)

        # Now configure the IPU to add the secondary IP
        secondary_ip = interface['target_ip']  # This will be 100.0.1.100, 100.0.2.100, etc.
        print_colored(f"   Adding secondary IP {secondary_ip} to IPU{i+1}...", Colors.BLUE)

        config_commands = [
            f"ip addr add {secondary_ip}/24 dev eth0",
            f"ip route add {secondary_ip.split('.')[0]}.{secondary_ip.split('.')[1]}.{secondary_ip.split('.')[2]}.0/24 dev eth0 2>/dev/null || true",
        ]

        for cmd in config_commands:
            success, output = ssh_command("100.0.0.100", cmd, 5)
            if success or "File exists" in str(output):
                print_colored(f"? Command executed: {cmd}", Colors.GREEN)
            else:
                print_colored(f"?? Command warning: {cmd} - {output}", Colors.YELLOW)

        # Test the new IP configuration by switching our host IP and testing
        print_colored(f"   Testing new IP configuration for IPU{i+1}...", Colors.BLUE)
        flush_interface_addresses(interface['name'])
        add_interface_ip(interface['name'], interface['host_ip'])  # Use the final host IP
        add_static_neighbor(secondary_ip, ipu_mac, interface['name'])

        time.sleep(2)
        success, _ = ping_host(secondary_ip)

        if success:
            print_colored(f"? IPU{i+1} responding at {secondary_ip}", Colors.GREEN)
        else:
            print_colored(f"?? IPU{i+1} configured but may need time to respond at {secondary_ip}", Colors.YELLOW)
            print_colored(f"   Continuing anyway - will verify in final test phase", Colors.BLUE)

    return True

def setup_multi_access(config: InterfaceConfig) -> bool:
    """Step 3: Set up multi-interface access with proper routing"""
    print_colored("\n=== Step 2: Set Up Multi-Interface Access ===", Colors.YELLOW)

    print_colored("1. Bringing up all interfaces and configuring...", Colors.BLUE)

    # Bring up all interfaces and configure with appropriate IPs
    for interface in config.interfaces:
        set_interface_state(interface['name'], "up")
        flush_interface_addresses(interface['name'])
        add_interface_ip(interface['name'], interface['host_ip'])

    # Clear and set up static neighbor entries
    print_colored("2. Setting up static neighbor entries...", Colors.BLUE)
    run_command("sudo ip neigh flush all")
    run_command("sudo ip route flush cache")

    time.sleep(2)

    # Add static entries for all IPUs
    success_count = 0
    for i, interface in enumerate(config.interfaces):
        ipu_mac = config.interface_macs[interface['name']]
        target_ip = interface['target_ip']

        success, _ = add_static_neighbor(target_ip, ipu_mac, interface['name'])
        if success:
            print_colored(f"? Static entry: {target_ip} ? {interface['name']} (IPU{i+1})", Colors.GREEN)
            success_count += 1

    # Add specific routes
    print_colored("3. Adding routes...", Colors.BLUE)
    for i, interface in enumerate(config.interfaces):
        target_ip = interface['target_ip']
        source_ip = interface['host_ip'].split('/')[0]
        add_route(f"{target_ip}/32", interface['name'], source_ip)

    print_colored("? Routes configured", Colors.GREEN)
    return success_count > 0

def test_multi_access(config: InterfaceConfig) -> dict:
    """Step 4: Test multi-interface access to all IPU devices"""
    print_colored("\n=== Step 3: Testing Multi-Interface Access ===", Colors.YELLOW)

    results = {}

    # Test each IPU
    for i, interface in enumerate(config.interfaces):
        ipu_name = f"ipu{i+1}"
        target_ip = interface['target_ip']

        print_colored(f"\n{i+1}. Testing IPU{i+1} ({target_ip})...", Colors.BLUE)
        success, _ = ping_host(target_ip, 3, 3)
        if success:
            print_colored(f"? IPU{i+1} ping successful", Colors.GREEN)

            # Test SSH
            success, hostname = ssh_command(target_ip, "hostname")
            if success and hostname:
                print_colored(f"? IPU{i+1} SSH successful: {hostname}", Colors.GREEN)
                results[ipu_name] = True
            else:
                print_colored(f"? IPU{i+1} SSH failed", Colors.RED)
                results[ipu_name] = False
        else:
            print_colored(f"? IPU{i+1} ping failed", Colors.RED)
            results[ipu_name] = False

    return results

def setup_acc_connections(config: InterfaceConfig) -> dict:
    """Step 5: Set up ACC connections via all IMCs"""
    print_colored("\n=== Step 4: Setting up ACC connections ===", Colors.YELLOW)

    acc_results = {}

    # Setup ACC connection for each IMC
    for i, interface in enumerate(config.interfaces):
        acc_name = f"acc{i+1}"
        imc_ip = interface['target_ip']

        print_colored(f"\n{i+1}. Setting up ACC{i+1} connection via IMC{i+1}...", Colors.BLUE)
        setup_imc_to_acc_connection(imc_ip, f"IMC{i+1}")

        # Test ACC connection
        if test_acc_connection(imc_ip, f"IMC{i+1}"):
            acc_results[acc_name] = True
        else:
            acc_results[acc_name] = False

    return acc_results

def create_ssh_aliases(config: InterfaceConfig) -> None:
    """Create SSH aliases for easy access to IPU devices"""
    print_colored("\n=== Creating SSH Aliases ===", Colors.YELLOW)

    # Get the original user (the one who ran sudo)
    original_user = os.environ.get('SUDO_USER', os.environ.get('USER', 'root'))
    if original_user == 'root':
        ssh_config_path = "/root/.ssh/config"
        ssh_dir = "/root/.ssh"
    else:
        ssh_config_path = f"/home/{original_user}/.ssh/config"
        ssh_dir = f"/home/{original_user}/.ssh"

    print_colored(f"Creating SSH config for user: {original_user}", Colors.BLUE)

    # Build SSH config dynamically based on configured interfaces
    ssh_config = "\n# IMC SSH Aliases\n"

    for i, interface in enumerate(config.interfaces):
        hostname = interface['target_ip']

        ssh_config += f"""Host IMC{i+1}
    HostName {hostname}
    User root
    HostKeyAlias imc-via-local{i+1}
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts
    ConnectTimeout 5

"""

    # Add IP address aliases to use same host key aliases as IMC entries
    ssh_config += "\n# Direct IP Access Aliases (using same host keys as IMC)\n"

    for i, interface in enumerate(config.interfaces):
        hostname = interface['target_ip']
        ssh_config += f"""Host {hostname}
    HostName {hostname}
    User root
    HostKeyAlias imc-via-local{i+1}
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts
    ConnectTimeout 5

"""

    ssh_config += "\n# ACC SSH Aliases (via ProxyJump through IMC)\n"

    for i, interface in enumerate(config.interfaces):
        ssh_config += f"""Host ACC{i+1}
    HostName {ACC_TARGET_IP}
    User root
    ProxyJump IMC{i+1}
    HostKeyAlias acc-via-imc{i+1}
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts
    ConnectTimeout 10

"""

    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir, mode=0o700)
        # Set correct ownership for the SSH directory
        if original_user != 'root':
            import pwd
            uid = pwd.getpwnam(original_user).pw_uid
            gid = pwd.getpwnam(original_user).pw_gid
            os.chown(ssh_dir, uid, gid)

    existing_config = ""
    if os.path.exists(ssh_config_path):
        with open(ssh_config_path, 'r') as f:
            existing_config = f.read()

    # Always ensure SSH aliases are properly configured
    # Clean up any existing IPU, IMC, or ACC entries and recreate them
    lines = existing_config.split('\n')
    filtered_lines = []
    skip_section = False

    for line in lines:
        # Check for IPU-related host entries (IMC, ACC, MEV, or IP addresses starting with 100.0)
        if line.strip().startswith('Host ') and (
            'mev' in line.lower() or 'imc' in line.lower() or 'acc' in line.lower() or
            re.search(r'100\.0\.\d+\.\d+', line)
        ):
            skip_section = True
            continue
        elif line.strip().startswith('Host ') and skip_section:
            skip_section = False
        elif skip_section and (line.strip().startswith('HostName') or
                             line.strip().startswith('User') or
                             line.strip().startswith('StrictHostKeyChecking') or
                             line.strip().startswith('ConnectTimeout') or
                             line.strip().startswith('ProxyJump') or
                             line.strip() == ''):
            continue

        if not skip_section:
            filtered_lines.append(line)

    # Write the cleaned config plus new aliases
    with open(ssh_config_path, 'w') as f:
        f.write('\n'.join(filtered_lines).rstrip() + ssh_config)
    os.chmod(ssh_config_path, 0o600)

    # Set correct ownership for the SSH config file
    if original_user != 'root':
        import pwd
        uid = pwd.getpwnam(original_user).pw_uid
        gid = pwd.getpwnam(original_user).pw_gid
        os.chown(ssh_config_path, uid, gid)

    # Show created aliases
    alias_list = ", ".join([f"ssh IMC{i+1}" for i in range(len(config.interfaces))])
    acc_alias_list = ", ".join([f"ssh ACC{i+1}" for i in range(len(config.interfaces))])
    print_colored(f"? SSH aliases created: {alias_list}, {acc_alias_list}", Colors.GREEN)

def show_final_results(config: InterfaceConfig, results: dict, acc_results: dict) -> bool:
    """Display final results and configuration information"""
    # Check if all IPUs are working
    all_ipu_working = all(results.values())

    if all_ipu_working:
        print_colored(f"\n?? SUCCESS: Multi-IPU access working! ({len(results)} devices)", Colors.GREEN)
        print_colored("\nAccess Information:", Colors.BLUE)

        # Show IMC access info
        for i, interface in enumerate(config.interfaces):
            ip_addr = interface['target_ip']
            print_colored(f"  IMC{i+1}: ssh IMC{i+1}  ({ip_addr})", Colors.GREEN)

        # Show ACC access info
        for i, interface in enumerate(config.interfaces):
            acc_name = f"acc{i+1}"
            if acc_results.get(acc_name, False):
                print_colored(f"  ACC{i+1}: ssh ACC{i+1}  (via IMC{i+1} ? {ACC_TARGET_IP})", Colors.GREEN)
            else:
                print_colored(f"  ACC{i+1}: Connection failed", Colors.RED)

        create_ssh_aliases(config)

        # Show current config
        print_colored("\n=== Current Configuration ===", Colors.YELLOW)
        print_colored("Neighbor entries:", Colors.BLUE)

        # Build pattern for all configured IPs
        ip_patterns = []
        for interface in config.interfaces:
            ip_base = '.'.join(interface['target_ip'].split('.')[0:3])
            ip_patterns.append(f"{ip_base}\.100")

        pattern = '|'.join(ip_patterns)
        success, output = run_command(f"ip neigh show | grep -E '({pattern})'")
        if success and output:
            for line in output.split('\n'):
                if line.strip():
                    print_colored(f"  {line}", Colors.GREEN)

        print_colored("Routes:", Colors.BLUE)
        success, output = run_command(f"ip route show | grep -E '({pattern})'")
        if success and output:
            for line in output.split('\n'):
                if line.strip():
                    print_colored(f"  {line}", Colors.GREEN)

        print_colored("\nConfiguration persists until reboot.", Colors.YELLOW)
        print_colored("Re-run this script after reboot to restore access.", Colors.YELLOW)

        return True
    else:
        print_colored(f"\n? Multi-IPU access not fully working", Colors.RED)

        for i, interface in enumerate(config.interfaces):
            ipu_name = f"ipu{i+1}"
            if results.get(ipu_name, False):
                print_colored(f"  IPU{i+1}: Working", Colors.GREEN)
            else:
                print_colored(f"  IPU{i+1}: Failed", Colors.RED)

        return False

def cleanup_ssh_known_hosts():
    """Clean up SSH known_hosts files to avoid host key conflicts with IPU devices"""
    print_colored("\n--- Cleaning SSH Known Hosts ---", Colors.BLUE)

    # Get the original user (the one who ran sudo)
    original_user = os.environ.get('SUDO_USER', os.environ.get('USER', 'root'))

    # Remove user's known_hosts
    if original_user == 'root':
        user_known_hosts = "/root/.ssh/known_hosts"
    else:
        user_known_hosts = f"/home/{original_user}/.ssh/known_hosts"

    success1, _ = run_command(f"sudo rm -f {user_known_hosts}")
    if success1:
        print_colored("  ✓ Removed user known_hosts file", Colors.GREEN)
    else:
        print_colored("  ! Could not remove user known_hosts file", Colors.YELLOW)

    # Remove root's known_hosts
    success2, _ = run_command("sudo rm -f /root/.ssh/known_hosts")
    if success2:
        print_colored("  ✓ Removed root known_hosts file", Colors.GREEN)
    else:
        print_colored("  ! Could not remove root known_hosts file", Colors.YELLOW)

    if success1 or success2:
        print_colored("  SSH host key conflicts should now be resolved", Colors.BLUE)

def main():
    print_colored("=== IPU Generic Multi-Interface Access Setup ===", Colors.YELLOW)
    print_colored("Robust script that works immediately after power cycle", Colors.BLUE)

    # Parse command line arguments
    enabled_interfaces = parse_arguments()
    print_colored(f"Configuring interfaces: {', '.join(enabled_interfaces)}", Colors.BLUE)

    # Clean up SSH known_hosts files to avoid host key conflicts
    cleanup_ssh_known_hosts()

    # Create interface configuration
    config = InterfaceConfig(enabled_interfaces)

    # Step 0: Initialize interfaces
    if not initialize_interfaces(config):
        return False

    # Step 1: Discover MAC addresses
    discovered_macs = discover_ipu_mac_addresses(config)
    if not discovered_macs:
        return False

    # Step 2: Configure IPUs with secondary IPs (skip first interface)
    if config.get_interface_count() > 1:
        if not configure_ipu_secondary_ips(config):
            return False

    # Step 3: Set up multi-interface access
    if not setup_multi_access(config):
        return False

    # Step 4: Test multi-interface access
    results = test_multi_access(config)

    # Step 5: Set up ACC connections
    acc_results = setup_acc_connections(config)

    # Step 6: Show results and create conveniences
    return show_final_results(config, results, acc_results)

if __name__ == "__main__":
    # Allow help to work without sudo by checking early
    if '--help' in sys.argv or '-h' in sys.argv:
        # Just call parse_arguments which will show help and exit
        parse_arguments()

    if os.geteuid() != 0:
        print(f"{Colors.RED}This script requires root privileges. Please run with sudo.{Colors.NC}")
        sys.exit(1)

    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Script interrupted by user{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        print_colored(f"\n? Unexpected error: {e}", Colors.RED)
        sys.exit(1)