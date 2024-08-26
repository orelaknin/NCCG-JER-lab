Zabbix API Python Scripts
This repository contains various Python scripts for interacting with the Zabbix API, focusing on managing hosts, tags, VLAN groups, and PDUs. The scripts are built using the zabbix_api library.

Prerequisites
Python 3.x
Zabbix API library: Install using pip install zabbix-api
PySNMP library (required for SNMP scripts): Install using pip install pysnmp
Scripts Overview
1. change_vlan_group.py
This script changes the VLAN group of specified hosts. It reads host names from a file and updates their VLAN group based on predefined settings.

2. get_script_id.py
A utility script to retrieve the script ID of a given Zabbix script by name. This is useful when you need the script ID for automation tasks.

3. pdu_power_cycle_ha.py
This script performs a power cycle operation for high-availability PDUs based on their SNMP data. It uses the pysnmp library to interact with PDUs and trigger the power cycle.

4. set_pdu_tag.py
The script assigns tags to PDUs based on their vendor information retrieved via SNMP. It checks the PDU’s details, identifies the vendor, and tags them accordingly in Zabbix.

5. update_inv.py
This script updates the inventory information of hosts. It is designed to fetch relevant inventory data and update it using the Zabbix API.

6. zab_read_tags.py
A script to read and display tags of specified Zabbix hosts. The tags are retrieved and printed for each host listed in a text file.

7. zab_set_tags.py
This script updates tags for hosts in Zabbix. It reads host names from a file and sets the tags based on predefined criteria or information from another file.

8. zab_set_tags2.py
An enhanced version of zab_set_tags.py, offering additional features like handling multiple tag formats or supporting more complex tagging logic.