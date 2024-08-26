from zabbix_api import ZabbixAPI

# Assuming you have established a connection to the Zabbix API (replace with your details)
zapi = ZabbixAPI(server="http://ladjzabbixc.jer.intel.com/zabbix/")
zapi.login("Del_Hosts", "$giga")

# Corrected JSON with list of tags
update_data = {
    "hostid": 10609,
    "tags": [
        {"tag": "OS", "value": "RHEL 7"}
    ]
}

# Send update request
zapi.host.update(update_data)

print("Successfully updated host tags.")