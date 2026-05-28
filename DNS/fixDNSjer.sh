#!/bin/bash

# Script to configure /etc/dhcp/dhclient.conf with custom DHCP settings
# This script creates a backup and replaces the content with Intel JER DNS configuration

set -e

DHCLIENT_CONF="/etc/dhcp/dhclient.conf"
BACKUP_FILE="${DHCLIENT_CONF}.backup.$(date +%Y%m%d_%H%M%S)"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "Error: This script must be run as root (use sudo)" 
   exit 1
fi

# Get the hostname
HOSTNAME=$(hostname)

if [[ -z "$HOSTNAME" ]]; then
    echo "Error: Could not determine hostname"
    exit 1
fi

echo "Hostname detected: $HOSTNAME"

# Create backup of the original file
if [[ -f "$DHCLIENT_CONF" ]]; then
    echo "Creating backup at: $BACKUP_FILE"
    cp "$DHCLIENT_CONF" "$BACKUP_FILE"
    echo "Backup created successfully"
else
    echo "Warning: $DHCLIENT_CONF does not exist, will create new file"
fi

# Write new configuration
echo "Writing new configuration to $DHCLIENT_CONF"
cat > "$DHCLIENT_CONF" << EOF
send host-name "${HOSTNAME}.jer.intel.com";
send dhcp-client-identifier = hardware;
request subnet-mask, broadcast-address, routers, domain-name, domain-name-servers, default-ip-ttl, ntp-servers, interface-mtu;
timeout 60;
retry 60;
send fqdn.fqdn "${HOSTNAME}.jer.intel.com.";
send fqdn.encoded on;
send fqdn.server-update on;
also request netbios-scope, netbios-name-servers, nis-domain, nis-servers, ntp-servers;
EOF

echo "Configuration updated successfully"
echo "You may need to restart the network service or run 'dhclient' to apply changes"
