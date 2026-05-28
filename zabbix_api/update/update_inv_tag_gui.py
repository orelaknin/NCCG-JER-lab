import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
from pyzabbix import ZabbixAPI
import sys

# Default Zabbix server details
default_server_url = "http://ladjzabbixc.jer.intel.com/zabbix/api_jsonrpc.php"
default_username = "Del_Hosts"
default_password = "$giga"

inventory_mapping = {
    "name": "Assign To",
    "type": "Type",
    "alias": "Nuc Hostname",
    "os_short": "Accessories",
    "serialno_a": "SVBoard Serial Number",
    "serialno_b": "SVBoard Unit",
    "tag": "Tag",
    "hardware": "PDU IP",
    "software_app_a": "PDU Host Port",
    "software_app_b": "PDU LTB Port",
    "type_full": "PDU EV Board Port",
    "software_app_c": "PDU Nuc Port",
    "os_full": "PDU RP Port",
    "contract_number": "Link Partner",
    "software_app_d": "Host Type",
    "hw_arch": "Unit State",
    "os": "OS",
    "software_app_e": "Group",
    "location": "Location"
}

def update_host_inventory_and_tags(zapi, host_name, row, tag_column, tag_value, tag_tag, output_text):
    try:
        hosts = zapi.host.get(filter={"host": host_name})
        if not hosts:
            output_text.insert(tk.END, f"Host not found: {host_name}\n")
            return
        host_id = hosts[0]["hostid"]

        inventory_data = {}
        for zabbix_field, excel_column in inventory_mapping.items():
            if excel_column in row.index and not pd.isna(row[excel_column]):
                inventory_data[zabbix_field] = str(row[excel_column])

        cleaned_inventory_data = {k: v for k, v in inventory_data.items() if not pd.isna(v)}
        if cleaned_inventory_data:
            update_data = {"hostid": host_id, "inventory_mode": 0, "inventory": cleaned_inventory_data}
            if not pd.isna(tag_value) and tag_value != '':
                existing_tags = zapi.host.get(hostids=host_id, selectTags="extend")[0]["tags"]
                existing_tags = [{k: v for k, v in tag.items() if k != "automatic" and k != tag_tag} for tag in existing_tags]
                new_tag = {"tag": tag_tag, "value": str(tag_value)}
                if new_tag not in existing_tags:
                    existing_tags.append(new_tag)
                update_data["tags"] = existing_tags
            zapi.host.update(**update_data)
            output_text.insert(tk.END, f"Successfully updated inventory and tags for host {host_name}.\n")
        else:
            output_text.insert(tk.END, f"No valid inventory data found for host {host_name}. Skipping update.\n")
    except Exception as e:
        output_text.insert(tk.END, f"Error updating {host_name}: {str(e)}\n")

def process_excel(file_path, server_url, username, password, tag_column, tag_tag, output_text):
    try:
        zapi = ZabbixAPI(server_url)
        zapi.login(user=username, password=password)
        output_text.insert(tk.END, "Connected to Zabbix API.\n")

        excel = pd.ExcelFile(file_path)
        output_text.insert(tk.END, f"Loaded Excel file: {file_path}\n")

        for sheet_name in excel.sheet_names:
            output_text.insert(tk.END, f"Processing sheet: {sheet_name}\n")
            inventory_df = pd.read_excel(excel, sheet_name=sheet_name)
            for index, row in inventory_df.iterrows():
                host_column = 'Host'
                host_name = row[host_column].strip() if isinstance(row[host_column], str) else row[host_column]
                if pd.isna(host_name) or host_name == '':
                    output_text.insert(tk.END, f"Skipping row {index + 2} due to empty host name.\n")
                    continue
                tag_value = row[tag_column] if tag_column in row else None
                update_host_inventory_and_tags(zapi, host_name, row, tag_column, tag_value, tag_tag, output_text)
            output_text.insert(tk.END, f"Finished processing sheet: {sheet_name}\n")
        output_text.insert(tk.END, "All sheets processed.\n")
    except Exception as e:
        output_text.insert(tk.END, f"Error: {str(e)}\n")

def create_gui():
    root = tk.Tk()
    root.title("Zabbix Inventory Updater")
    root.geometry("600x650")

    # Server URL
    server_url_var = tk.StringVar(value=default_server_url)
    tk.Label(root, text="Zabbix Server URL:").pack(pady=5)
    tk.Entry(root, textvariable=server_url_var, width=50).pack(pady=5)

    # File path
    file_path_var = tk.StringVar()
    tk.Label(root, text="Excel File Path:").pack(pady=5)
    file_entry = tk.Entry(root, textvariable=file_path_var, width=50)
    file_entry.pack(pady=5)
    tk.Button(root, text="Browse", command=lambda: file_path_var.set(filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")]))).pack(pady=5)

    # Tag column
    tag_column_var = tk.StringVar()
    tk.Label(root, text="Tag Column Name:").pack(pady=5)
    tk.Entry(root, textvariable=tag_column_var, width=30).pack(pady=5)

    # Tag name
    tag_tag_var = tk.StringVar()
    tk.Label(root, text="Tag Name:").pack(pady=5)
    tk.Entry(root, textvariable=tag_tag_var, width=30).pack(pady=5)

    # Output text area
    output_text = tk.Text(root, height=15, width=70)
    output_text.pack(pady=10)

    # Run button
    def run_script():
        file_path = file_path_var.get()
        server_url = server_url_var.get()
        username = username_var.get()
        password = password_var.get()
        tag_column = tag_column_var.get()
        tag_tag = tag_tag_var.get()
        if not all([file_path, server_url, username, password, tag_column, tag_tag]):
            messagebox.showerror("Error", "Please fill all fields!")
            return
        output_text.delete(1.0, tk.END)
        process_excel(file_path, server_url, username, password, tag_column, tag_tag, output_text)

    tk.Button(root, text="Run Update", command=run_script).pack(pady=5)
    tk.Button(root, text="Exit", command=root.quit).pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    create_gui()