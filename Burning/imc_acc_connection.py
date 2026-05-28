class Colors:
    CYAN = '\033[1;36m'
    YELLOW = '\033[1;33m'
    GREEN = '\033[1;32m'
    NC = '\033[0m'  # No Color
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

def get_ifconfig_summary():
    try:
        output = subprocess.check_output(['ifconfig', '-a'], encoding='utf-8')
    except Exception as e:
        print(f"Error running ifconfig: {e}")
        return []

    interfaces = re.split(r'\n(?=\S)', output)
    summary = []
    for iface in interfaces:
        lines = iface.strip().split('\n')
        if not lines:
            continue
        name = lines[0].split()[0]
        if name == 'lo:':
            continue  # Skip loopback interface
        mac = None
        inet = None
        for line in lines:
            mac_match = re.search(r'(ether|HWaddr) ([0-9a-fA-F:]{17})', line)
            if mac_match:
                mac = mac_match.group(2)
            inet_match = re.search(r'inet (addr:)?([0-9.]+)', line)
            if inet_match:
                inet = inet_match.group(2)
        # Filter out interfaces with IPs starting with 10.12, 10.189, or 143
        skip = False
        if inet:
            if inet.startswith('10.12') or inet.startswith('10.189') or inet.startswith('143.'):
                skip = True
        if not skip:
            summary.append({'name': name, 'ip': inet, 'mac': mac})
    return summary

def present_interfaces_and_run_mev():
    summary = get_ifconfig_summary()
    if not summary:
        print("No interfaces found.")
        return
    print(f"\n{Colors.YELLOW}Available Interfaces:{Colors.NC}")
    for idx, iface in enumerate(summary, 1):

        print(f"{Colors.CYAN}{idx}. {iface['name']} {Colors.NC}: IP={Colors.GREEN}{iface['ip'] or 'N/A'}{Colors.NC}, MAC={iface['mac'] or 'N/A'}")
    while True:
        try:
            choice = input("\nSelect interface number(s) to run mev_dual_imc_acc_connection.py on (comma-separated, e.g. 1,3,4 or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                print("Exiting.")
                return
            indices = [int(x) for x in choice.split(',') if x.strip().isdigit()]
            if not indices or any(i < 1 or i > len(summary) for i in indices):
                print("Invalid selection. Try again.")
                continue
            selected_ifaces = []
            for i in indices:
                name = summary[i-1]['name']
                if name.endswith(":"):
                    name = name[:-1]
                selected_ifaces.append(name)
            break
        except ValueError:
            print("Invalid input. Enter numbers separated by commas or 'q'.")

    # Run mev_dual_imc_acc_connection.py once with all selected interfaces as arguments
    iface_args = [f'--{iface}' for iface in selected_ifaces]
    print(f"\nRunning mev_dual_imc_acc_connection.py on {', '.join(selected_ifaces)}...\n")
    try:
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'mev_dual_imc_acc_connection.py')] + iface_args, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running mev_dual_imc_acc_connection.py: {e}")


if __name__ == "__main__":
    present_interfaces_and_run_mev()