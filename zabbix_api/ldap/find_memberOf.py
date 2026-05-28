from ldap3 import Server, Connection, ALL

server = Server('corpldap.intel.com', port=3268, get_info=ALL)
conn = Connection(server, 'support01@intel.com', 'qawsedrftg1029384756!', auto_bind=True)
conn.search('dc=corp,dc=intel,dc=com', '(sAMAccountName=cmallakx)', attributes=['memberOf'])

for entry in conn.entries:
    print(entry)

    # Check if the 'memberOf' attribute is present
    if 'memberOf' in entry.entry_attributes_as_dict:
        member_of = entry.entry_attributes_as_dict['memberOf']
        print("Groups the user belongs to:")
        for group in member_of:
            print(group)
    else:
        print("memberOf attribute not found or user is not part of any groups.")
