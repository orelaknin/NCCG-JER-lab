#!/usr/bin/env python3
"""
List all IMC* SSH connections from ~/.ssh/config
"""
import os
import re

def list_imc_ssh_connections(ssh_config_path=None):
    """
    Reads the SSH config file and lists all Host entries starting with 'IMC'.
    Returns a list of hostnames (e.g., IMC1, IMC2, ...).
    """
    if ssh_config_path is None:
        ssh_config_path = os.path.expanduser('~/.ssh/config')
    if not os.path.exists(ssh_config_path):
        print(f"SSH config file not found: {ssh_config_path}")
        return []

    imc_hosts = []
    with open(ssh_config_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Match lines like: Host IMC1, Host IMC2, etc.
            m = re.match(r'^Host\s+(IMC\S*)', line)
            if m:
                imc_hosts.append(m.group(1))
    return imc_hosts

if __name__ == "__main__":
    hosts = list_imc_ssh_connections()
    if hosts:
        print("IMC* SSH connections found in ~/.ssh/config:")
        for h in hosts:
            print(f"  {h}")
    else:
        print("No IMC* SSH connections found in ~/.ssh/config.")
