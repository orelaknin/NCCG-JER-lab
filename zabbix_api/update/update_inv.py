import pandas as pd
from zabbix_api import ZabbixAPI

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "Del_Hosts"
password = "$giga"

# Path to the Excel file containing host inventory
excel_file = r"C:\Scripts\HA_ZAB.xlsx"


# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

def update_host_inventory(host_name, inventory_data):
    """
    Updates a host with the specified inventory data.

    Args:
        host_name (str): Name of the host to update.
        inventory_data (dict): Dictionary representing inventory data.
    """

    # Get host ID
    hosts = zapi.host.get({"filter": {"host": host_name}})
    if hosts:
        host_id = hosts[0]["hostid"]
    else:
        print("Host not found:", host_name)
        return  # Skip to the next host if not found

    # Remove NaN values from inventory data
    cleaned_inventory_data = {k: v for k, v in inventory_data.items() if not pd.isna(v)}

    # Update host inventory if there are non-NaN values
    if cleaned_inventory_data:
        # Update host inventory
        zapi.host.update(
            {
                "hostid": host_id,
		"inventory_mode": 0,
                "inventory": cleaned_inventory_data,
            }
        )

        print(f"Successfully updated inventory for host {host_name}.")
    else:
        print(f"No valid inventory data found for host {host_name}. Skipping update.")


# Read all sheets from the Excel file
excel = pd.ExcelFile(excel_file)

# Iterate over each sheet in the Excel file
for sheet_name in excel.sheet_names:
    print(f"Processing sheet: {sheet_name}")
    
    # Read the current sheet
    inventory_df = pd.read_excel(excel, sheet_name=sheet_name)
    
    # Iterate over each row in the DataFrame
    for index, row in inventory_df.iterrows():
        host_name = row['system name']  # Assuming 'system name' is the column containing host names
        
        # Skip rows where host name is empty
        if pd.isna(host_name) or host_name == '':
            print(f"Skipping row {index + 2} due to empty host name.")
            continue

        # Construct inventory data
        inventory_data = {
            "software_app_e": row['Group type'],
            "alias": row['NUC'],
            "hardware": row['PowerPDU IP'],
            "software_app_a": row['PDU Port'],
            "name": row['Assign to'],
            "contract_number": row['LP Host'],
            "location": row['location'],
            # Add more tags as needed
        }
        
        update_host_inventory(host_name, inventory_data)

    print(f"Finished processing sheet: {sheet_name}")

print("All sheets processed.")
