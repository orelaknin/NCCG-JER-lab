import tkinter as tk
from tkinter import ttk, messagebox
from pyzabbix import ZabbixAPI
import sys

# Default Zabbix server details
default_server_url = "http://nccg-zabbix.jer.intel.com/zabbix/api_jsonrpc.php"
default_username = "Del_Hosts"
default_password = "$giga"

# Inventory mapping for custom display names
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

def fetch_host_info(zapi, host_name, tree):
    """Fetch host information and populate the Treeview with custom inventory names."""
    try:
        tree.delete(*tree.get_children())  # Clear previous data
        hosts = zapi.host.get(
            filter={"host": host_name},
            selectInventory="extend",
            selectTags="extend",
            selectInterfaces="extend",
            output="extend"
        )

        if not hosts:
            messagebox.showinfo("Result", f"No host found with name: {host_name}")
            return None, None

        host = hosts[0]
        host_id = host["hostid"]

        # Populate Treeview with host data
        tree.insert("", "end", text="Basic Details", open=True)
        tree.insert("", "end", values=("Host ID", host["hostid"]))
        tree.insert("", "end", values=("Name", host["name"]))
        tree.insert("", "end", values=("Status", "Enabled" if host["status"] == "0" else "Disabled"))
        ip = host["interfaces"][0]["ip"] if host.get("interfaces") else "N/A"
        tree.insert("", "end", values=("IP Address", ip))

        # Inventory with custom names
        tree.insert("", "end", text="Inventory", open=True)
        if host.get("inventory"):
            for zabbix_key, display_name in inventory_mapping.items():
                value = host["inventory"].get(zabbix_key, "")
                if value:
                    tree.insert("", "end", values=(display_name, value))
        else:
            tree.insert("", "end", values=("No inventory data", ""))

        # Tags
        tree.insert("", "end", text="Tags", open=True)
        if host.get("tags"):
            for tag in host["tags"]:
                tree.insert("", "end", values=(tag["tag"], tag["value"]))
        else:
            tree.insert("", "end", values=("No tags assigned", ""))

        return zapi, host_id

    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch host info: {str(e)}")
        return None, None

def execute_zabbix_script(zapi, host_id, script_id, script_name):
    """Execute a Zabbix script on the specified host."""
    try:
        if not zapi or not host_id:
            messagebox.showerror("Error", "No host selected or connection failed.")
            return
        result = zapi.script.execute(scriptid=script_id, hostid=host_id)
        messagebox.showinfo(f"Script: {script_name}", f"Result: {result.get('value', 'No response')}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to execute {script_name}: {str(e)}")

def create_gui():
    root = tk.Tk()
    root.title("Zabbix Host Info Viewer")
    root.geometry("1000x700")  # Increased width to accommodate side-by-side layout
    root.resizable(True, True)
    root.configure(bg="#f0f0f0")

    # Style configuration
    style = ttk.Style()
    style.configure("TLabel", font=("Helvetica", 10), background="#f0f0f0")
    style.configure("TButton", font=("Helvetica", 10), padding=5)
    style.configure("TEntry", font=("Helvetica", 10))
    style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
    style.configure("Treeview", font=("Helvetica", 10))

    # Connection Frame
    conn_frame = ttk.LabelFrame(root, text="Zabbix Connection", padding=10)
    conn_frame.pack(padx=10, pady=5, fill="x")

    server_url_var = tk.StringVar(value=default_server_url)
    ttk.Label(conn_frame, text="Zabbix Server URL:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    ttk.Entry(conn_frame, textvariable=server_url_var, width=50).grid(row=0, column=1, padx=5, pady=5)

    username_var = tk.StringVar(value=default_username)
    ttk.Label(conn_frame, text="Username:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
    ttk.Entry(conn_frame, textvariable=username_var, width=30).grid(row=1, column=1, padx=5, pady=5)

    password_var = tk.StringVar(value=default_password)
    ttk.Label(conn_frame, text="Password:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
    ttk.Entry(conn_frame, textvariable=password_var, width=30, show="*").grid(row=2, column=1, padx=5, pady=5)

    # Search Frame
    search_frame = ttk.LabelFrame(root, text="Host Search", padding=10)
    search_frame.pack(padx=10, pady=5, fill="x")

    host_name_var = tk.StringVar()
    ttk.Label(search_frame, text="Host Name:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    ttk.Entry(search_frame, textvariable=host_name_var, width=30).grid(row=0, column=1, padx=5, pady=5)
    search_button = ttk.Button(search_frame, text="Search Host")
    search_button.grid(row=0, column=2, padx=5, pady=5)

    # Container Frame for Output and Buttons
    content_frame = ttk.Frame(root)
    content_frame.pack(padx=10, pady=5, fill="both", expand=True)

    # Output Frame with Treeview (Left)
    output_frame = ttk.LabelFrame(content_frame, text="Host Information", padding=10)
    output_frame.pack(side=tk.LEFT, fill="both", expand=True)

    tree = ttk.Treeview(output_frame, columns=("Key", "Value"), show="tree headings", height=20)
    tree.heading("Key", text="Property")
    tree.heading("Value", text="Details")
    tree.column("#0", width=0, stretch=tk.NO)
    tree.column("Key", width=200, anchor="w")
    tree.column("Value", width=400, anchor="w")
    tree.pack(side=tk.LEFT, fill="both", expand=True)

    scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=tree.yview)
    scrollbar.pack(side=tk.RIGHT, fill="y")
    tree.configure(yscrollcommand=scrollbar.set)

    # Button Frame for Scripts (Right)
    button_frame = ttk.LabelFrame(content_frame, text="Script Actions", padding=10)
    button_frame.pack(side=tk.RIGHT, fill="y", padx=10)

    zapi_instance = [None]
    host_id_var = [None]

    def search_host():
        server_url = server_url_var.get()
        username = username_var.get()
        password = password_var.get()
        host_name = host_name_var.get()
        if not all([server_url, username, password, host_name]):
            messagebox.showerror("Error", "Please fill all fields!")
            return
        zapi = ZabbixAPI(server_url)
        zapi.login(user=username, password=password)
        zapi_instance[0], host_id_var[0] = fetch_host_info(zapi, host_name, tree)

    search_button.configure(command=search_host)

    # Script buttons (replace scriptid with actual IDs from your Zabbix)
    script_buttons = [
        {"name": "PDU EV Board Power Off", "scriptid": "1"},
        {"name": "PDU EV Board Power On", "scriptid": "2"},
        {"name": "PDU Host Power Cycle", "scriptid": "3"},
        {"name": "PDU Host Power Off", "scriptid": "4"},
        {"name": "PDU Host Power On", "scriptid": "5"},
        {"name": "PDU LTB Power Cycle", "scriptid": "6"},
        {"name": "PDU NUC Power Cycle", "scriptid": "7"}
    ]

    for i, script in enumerate(script_buttons):
        ttk.Button(button_frame, text=script["name"],
                   command=lambda s=script: execute_zabbix_script(zapi_instance[0], host_id_var[0], s["scriptid"], s["name"])).grid(row=i, column=0, padx=5, pady=5, sticky="ew")

    # Exit Button at the bottom of button_frame
    ttk.Button(button_frame, text="Exit", command=root.quit).grid(row=len(script_buttons), column=0, pady=10, sticky="ew")

    root.mainloop()

if __name__ == "__main__":
    create_gui()