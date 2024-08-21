import pandas as pd
from zabbix_api import ZabbixAPI

# Replace with your Zabbix server URL
server_url = "http://ladjzabbixc.jer.intel.com/zabbix/"

# Replace with your Zabbix API credentials
username = "Del_Hosts"
password = "$giga"

# Path to the Excel file containing host inventory
excel_file = r"C:\Scripts\test.xlsx"

# Connect to the Zabbix API
zapi = ZabbixAPI(server=server_url)
zapi.login(username, password)

def update_host_inventory_and_tags(host_name, inventory_data, tag_column, tag_value):
    """
    Updates a host with the specified inventory data and tags.
    
    Args:
        host_name (str): Name of the host to update.
        inventory_data (dict): Dictionary representing inventory data.
        tag_column (str): Name of the column to use as tag.
        tag_value (str): Value of the tag.
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
        # Prepare the update data
        update_data = {
            "hostid": host_id,
            "inventory_mode": 0,
            "inventory": cleaned_inventory_data,
        }

        # Add tag if it's not empty
        if not pd.isna(tag_value) and tag_value != '':
            existing_tags = zapi.host.get({"hostids": host_id, "selectTags": "extend"})
            existing_tags = existing_tags[0]["tags"]
            print("1Existing tags:", existing_tags)
            # Remove "automatic" parameter from existing tags (if present)
            existing_tags = [{k: v for k, v in tag.items() if k != "automatic"} for tag in existing_tags]
            new_tag = {"tag": tag_column, "value": str(tag_value)}
            print("new tags:", new_tag)
            if new_tag not in existing_tags:
                existing_tags.append(new_tag)
            
            print("Existing tags:", existing_tags)
            # Update host
            zapi.host.update({"hostid": host_id, "tags": existing_tags})

        print(f"Successfully updated inventory and tags for host {host_name}.")
    else:
        print(f"No valid inventory data found for host {host_name}. Skipping update.")

# Read all sheets from the Excel file
excel = pd.ExcelFile(excel_file)

# Specify the column to use as a tag
tag_column = input("Enter the column name to use as a tag: ")

# Iterate over each sheet in the Excel file
for sheet_name in excel.sheet_names:
    print(f"Processing sheet: {sheet_name}")
    
    # Read the current sheet
    inventory_df = pd.read_excel(excel, sheet_name=sheet_name)
    
    # Iterate over each row in the DataFrame
    for index, row in inventory_df.iterrows():
        host_column= 'Host'
        host_name = row[host_column].strip() if isinstance(row[host_column], str) else row[host_column]  # Assuming 'Host' is the column containing host names
        
        # Skip rows where host name is empty
        if pd.isna(host_name) or host_name == '':
            print(f"Skipping row {index + 2} due to empty host name.")
            continue

        # Construct inventory data
        inventory_data = {
            "software_app_e": row['Group'],
            "alias": row['NUC'],
            "hardware": row['PowerPDU IP'],
            "software_app_a": row['Port'],
            "name": row['User'],
            "contract_number": row['Related'],
            "location": row['Table'],
            "os_short": row['Accessroies'],
            "type_full": row['EV_BOARD'],
            "os_full": row['RP'],
            # Add more tags as needed
        }
        
        # Get the tag value from the specified column
        tag_value = row[tag_column] if tag_column in row else None

        update_host_inventory_and_tags(host_name, inventory_data, tag_column, tag_value)
    
    print(f"Finished processing sheet: {sheet_name}")

print("All sheets processed.")