Zabbix Automation Scripts
This repository contains Python scripts for automating tasks with the Zabbix API. These scripts provide functionality to create, update, and delete hosts in a Zabbix server, along with additional features like dynamic template assignment and SNMP-based vendor detection.

Prerequisites
Python 3.x
Required Python libraries:
zabbix-api
pysnmp (only for SNMP-based scripts)
To install the dependencies, run:

bash
Copy code
pip install zabbix-api pysnmp
Scripts Overview
1. Create Hosts with SNMP Interface (create_hosts_snmp.py)
This script reads a list of IP addresses from a text file (ips.txt) and creates corresponding hosts in Zabbix with SNMP v1 interfaces. The script also pings each IP to check its reachability and uses DNS to resolve the hostnames.

Key Features:
IP-based host creation
SNMP v1 interface configuration
Automatic hostname resolution via DNS
Fixed template assignment
2. Create Hosts with Dynamic SNMP Template Assignment (create_hosts_dynamic_snmp.py)
This script extends the first script by dynamically assigning a template based on the detected SNMP vendor. The vendor is identified using an SNMP GET operation on the OID 1.3.6.1.2.1.1.1.0.

Key Features:
SNMP GET-based vendor detection
Dynamic template assignment based on vendor
Handles multiple vendor types (e.g., Aten, Raritan, Eaton)
Host existence check before creation
3. Delete a Single Host by Name (delete_single_host.py)
This script deletes a single host in Zabbix by specifying its name. It retrieves the host ID using the provided hostname and performs the deletion if the host is found.

Key Features:
Simple deletion of a specified host by name
Provides feedback if the host is not found
4. Batch Delete Hosts from File (delete_hosts_batch.py)
This script reads a list of hostnames from a file (hosts_delete.txt) and deletes each host from Zabbix. It is useful for batch deletion operations.

Key Features:
Batch deletion of hosts based on a file input
Host existence check before deletion
Provides feedback if hosts are not found
Usage Instructions
Configure Zabbix API Settings:
Update the following details in each script:

server_url: Your Zabbix server URL.
username and password: Your Zabbix API credentials.
Other settings such as snmp_community, group_id, and template_id where applicable.
Running the Scripts:
Create Hosts with SNMP Interface:

bash
Copy code
python create_hosts_snmp.py
Create Hosts with Dynamic SNMP Template Assignment:

bash
Copy code
python create_hosts_dynamic_snmp.py
Delete a Single Host by Name:

bash
Copy code
python delete_single_host.py
Batch Delete Hosts from File:

bash
Copy code
python delete_hosts_batch.py
Input Files:
For the creation scripts, ensure that ips.txt contains the list of IP addresses (one per line).
For the batch deletion script, ensure that hosts_delete.txt contains the list of hostnames to delete (one per line).