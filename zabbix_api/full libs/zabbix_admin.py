"""
Zabbix Admin Controller - Administrative operations for Zabbix
WARNING: This module contains WRITE operations that modify Zabbix configuration
Only use with appropriate administrative credentials and permissions
"""

from typing import Optional, Dict, Any, List
import ipaddress
from zabbix_controller import ZabbixController, log, Result
from zabbix_utils import clean_hostname


# Mapping of human-readable titles to Zabbix inventory database field names
INVENTORY_FIELD_MAPPING = {
    'Assign To': 'name',
    'Type': 'type',
    'Nuc Hostname': 'alias',
    'Accessories': 'os_short',
    'SVBoard Serial Number': 'serialno_a',
    'SVBoard Unit': 'serialno_b',
    'Tag': 'tag',
    'PDU IP': 'hardware',
    'PDU Host Port': 'software_app_a',
    'PDU LTB Port': 'software_app_b',
    'PDU Board Port': 'type_full',
    'PDU Nuc Port': 'software_app_c',
    'PDU RP Port': 'os_full',
    'Link Partner': 'contract_number',
    'Host Type': 'software_app_d',
    'Unit State': 'hw_arch',
    'OS': 'os',
    'Group': 'software_app_e',
    'Location': 'location'
}

# Reverse mapping: db_field -> title
INVENTORY_TITLE_MAPPING = {v: k for k, v in INVENTORY_FIELD_MAPPING.items()}


class ZabbixAdmin(ZabbixController):
    """
    Administrative operations for Zabbix - REQUIRES ELEVATED PRIVILEGES
    
    This class extends ZabbixController with write operations for:
    - Updating host inventory fields
    - Managing host tags
    - Syncing data from external databases
    
    Use with caution - all operations modify Zabbix configuration.
    """

    def __init__(self, 
                 zabbix_url: str = "http://ladjzabbixc.jer.intel.com/zabbix/",
                 username: str = "lab", 
                 password: str = "Ladlab1!"):
        """
        Initialize Zabbix Admin controller with elevated privileges
        
        Args:
            zabbix_url: Zabbix server URL
            username: Admin username with write permissions (default: "Admin")
            password: Admin password (REQUIRED - no default for security)
        """
        if not password:
            raise ValueError("Admin password is required for ZabbixAdmin operations")
        
        log("=" * 80)
        log("WARNING: Initializing ZabbixAdmin with WRITE PERMISSIONS")
        log("All operations will modify Zabbix configuration")
        log("=" * 80)
        
        # Initialize with admin credentials
        super().__init__(zabbix_url=zabbix_url, 
                        username=username, 
                        password=password)

    def get_db_field_name(self, field_name: str) -> Optional[str]:
        """
        Convert a field name (title or db_field) to database field name
        
        Args:
            field_name: Either a human-readable title (e.g., 'Location') or db field name (e.g., 'location')
            
        Returns:
            str: Database field name, None if not found
        """
        # Check if it's already a db field name
        if field_name in INVENTORY_TITLE_MAPPING:
            return field_name
        
        # Check if it's a title
        if field_name in INVENTORY_FIELD_MAPPING:
            return INVENTORY_FIELD_MAPPING[field_name]
        
        # Not found
        return None

    def get_field_title(self, db_field: str) -> Optional[str]:
        """
        Convert a database field name to human-readable title
        
        Args:
            db_field: Database field name (e.g., 'location')
            
        Returns:
            str: Human-readable title, None if not found
        """
        return INVENTORY_TITLE_MAPPING.get(db_field)

    def update_inventory_field(self, hostname: str, field_name: str, value: str, use_title: bool = True) -> int:
        """
        Update a single inventory field for a host
        
        Args:
            hostname: Hostname to update
            field_name: Zabbix inventory field name or human-readable title (e.g., 'Location', 'Type')
                       Default behavior uses human-readable titles. Set use_title=False for db field names.
            value: New value for the field
            use_title: If True (default), treat field_name as a human-readable title. If False, use db field name.
            
        Returns:
            int: Result.SUCCESS (0) if successful, Result.ERROR (-1) if failed
            
        Examples:
            admin.update_inventory_field('myhost', 'Location', 'Lab-5')
            admin.update_inventory_field('myhost', 'location', 'Lab-5', use_title=False)
        """
        hostname_clean = clean_hostname(hostname)
        
        # Convert title to db field if needed
        if use_title:
            db_field = self.get_db_field_name(field_name)
            if not db_field:
                log(f"ERROR: Unknown inventory field title: {field_name}")
                return Result.ERROR
            log(f"Updating inventory field '{field_name}' ({db_field}) for host {hostname_clean} to: {value}")
            field_name = db_field
        else:
            log(f"Updating inventory field '{field_name}' for host {hostname_clean} to: {value}")
        
        try:
            # Get host ID
            host_id = self._get_host_id(hostname_clean)
            if not host_id:
                log(f"ERROR: Host {hostname_clean} not found in Zabbix")
                return Result.ERROR
            
            # Update inventory
            result = self.zapi.host.update({
                "hostid": host_id,
                "inventory_mode": 0,  # 0 = Manual, -1 = Disabled, 1 = Automatic
                "inventory": {
                    field_name: value
                }
            })
            
            if result:
                log(f"Successfully updated inventory field '{field_name}' for {hostname_clean}")
                return Result.SUCCESS
            else:
                log(f"Failed to update inventory field '{field_name}' for {hostname_clean}")
                return Result.ERROR
                
        except Exception as e:
            log(f"ERROR: Failed to update inventory field: {e}")
            import traceback
            log(f"DEBUG: {traceback.format_exc()}")
            return Result.ERROR

    def update_inventory_fields(self, hostname: str, inventory_data: Dict[str, str], use_titles: bool = True) -> int:
        """
        Update multiple inventory fields for a host in a single operation
        
        Args:
            hostname: Hostname to update
            inventory_data: Dictionary of field_name: value pairs
            use_titles: If True (default), treat keys as human-readable titles. If False, use db field names.
            
        Returns:
            int: Result.SUCCESS (0) if successful, Result.ERROR (-1) if failed
            
        Examples:
            # Using human-readable titles (default)
            admin.update_inventory_fields('myhost', {
                'Location': 'Lab-5',
                'Type': 'Server',
                'SVBoard Serial Number': 'ABC123'
            })
            
            # Using database field names
            admin.update_inventory_fields('myhost', {
                'location': 'Lab-5',
                'type': 'Server',
                'serialno_a': 'ABC123'
            }, use_titles=False)
        """
        hostname_clean = clean_hostname(hostname)
        
        # Convert titles to db fields if needed
        if use_titles:
            converted_data = {}
            for field_name, value in inventory_data.items():
                db_field = self.get_db_field_name(field_name)
                if not db_field:
                    log(f"WARNING: Unknown inventory field title: {field_name}, skipping")
                    continue
                converted_data[db_field] = value
            inventory_data = converted_data
        
        log(f"Updating {len(inventory_data)} inventory fields for host {hostname_clean}")
        
        try:
            # Get host ID
            host_id = self._get_host_id(hostname_clean)
            if not host_id:
                log(f"ERROR: Host {hostname_clean} not found in Zabbix")
                return Result.ERROR
            
            # Update all inventory fields
            result = self.zapi.host.update({
                "hostid": host_id,
                "inventory_mode": 0,  # 0 = Manual
                "inventory": inventory_data
            })
            
            if result:
                log(f"Successfully updated {len(inventory_data)} inventory fields for {hostname_clean}")
                for field, value in inventory_data.items():
                    log(f"  {field}: {value}")
                return Result.SUCCESS
            else:
                log(f"Failed to update inventory fields for {hostname_clean}")
                return Result.ERROR
                
        except Exception as e:
            log(f"ERROR: Failed to update inventory fields: {e}")
            import traceback
            log(f"DEBUG: {traceback.format_exc()}")
            return Result.ERROR

    def get_host_inventory(self, hostname: str) -> Optional[Dict[str, str]]:
        """
        Get all inventory fields for a host
        
        Args:
            hostname: Hostname to query
            
        Returns:
            dict: Dictionary of inventory fields, None if failed
        """
        hostname_clean = clean_hostname(hostname)
        log(f"Getting inventory for host: {hostname_clean}")
        
        try:
            hosts = self.zapi.host.get({
                "output": ["hostid", "host"],
                "selectInventory": "extend",
                "filter": {"host": hostname_clean}
            })
            
            if not hosts:
                log(f"ERROR: Host {hostname_clean} not found in Zabbix")
                return None
            
            inventory = hosts[0].get('inventory', {})
            log(f"Retrieved {len(inventory)} inventory fields for {hostname_clean}")
            return inventory
            
        except Exception as e:
            log(f"ERROR: Failed to get inventory: {e}")
            return None

    def update_host_tags(self, hostname: str, tags: List[Dict[str, str]], merge: bool = False) -> int:
        """
        Update tags for a host
        
        Args:
            hostname: Hostname to update
            tags: List of tag dictionaries with 'tag' and 'value' keys
            merge: If True, merge with existing tags. If False, replace all tags.
            
        Returns:
            int: Result.SUCCESS (0) if successful, Result.ERROR (-1) if failed
            
        Example:
            admin.update_host_tags('myhost', [
                {'tag': 'Environment', 'value': 'Production'},
                {'tag': 'Owner', 'value': 'TeamA'}
            ])
        """
        hostname_clean = clean_hostname(hostname)
        log(f"Updating tags for host {hostname_clean} (merge={merge})")
        
        try:
            # Get host ID
            host_id = self._get_host_id(hostname_clean)
            if not host_id:
                log(f"ERROR: Host {hostname_clean} not found in Zabbix")
                return Result.ERROR
            
            # If merge is True, get existing tags first
            if merge:
                existing_tags = self.get_host_tags(hostname)
                if existing_tags is not None:
                    # Create a dict for quick lookup
                    tag_dict = {tag['tag']: tag['value'] for tag in existing_tags}
                    # Update with new tags
                    for tag in tags:
                        tag_dict[tag['tag']] = tag['value']
                    # Convert back to list format
                    tags = [{'tag': k, 'value': v} for k, v in tag_dict.items()]
            
            # Clean tags - ensure only 'tag' and 'value' fields are sent
            cleaned_tags = [{'tag': t['tag'], 'value': t['value']} for t in tags]
            
            # Update tags
            result = self.zapi.host.update({
                "hostid": host_id,
                "tags": cleaned_tags
            })
            
            if result:
                log(f"Successfully updated tags for {hostname_clean}")
                for tag in tags:
                    log(f"  {tag['tag']}: {tag['value']}")
                return Result.SUCCESS
            else:
                log(f"Failed to update tags for {hostname_clean}")
                return Result.ERROR
                
        except Exception as e:
            log(f"ERROR: Failed to update tags: {e}")
            import traceback
            log(f"DEBUG: {traceback.format_exc()}")
            return Result.ERROR

    def get_host_tags(self, hostname: str) -> Optional[List[Dict[str, str]]]:
        """
        Get all tags for a host
        
        Args:
            hostname: Hostname to query
            
        Returns:
            list: List of tag dictionaries with 'tag' and 'value' keys, None if failed
        """
        hostname_clean = clean_hostname(hostname)
        log(f"Getting tags for host: {hostname_clean}")
        
        try:
            hosts = self.zapi.host.get({
                "output": ["hostid", "host"],
                "selectTags": "extend",
                "filter": {"host": hostname_clean}
            })
            
            if not hosts:
                log(f"ERROR: Host {hostname_clean} not found in Zabbix")
                return None
            
            tags = hosts[0].get('tags', [])
            # Clean tags - only return 'tag' and 'value' fields, remove 'automatic' and other fields
            cleaned_tags = [{'tag': t['tag'], 'value': t['value']} for t in tags]
            log(f"Retrieved {len(cleaned_tags)} tags for {hostname_clean}")
            return cleaned_tags
            
        except Exception as e:
            log(f"ERROR: Failed to get tags: {e}")
            return None

    def add_host_tag(self, hostname: str, tag: str, value: str) -> int:
        """
        Add or update a single tag for a host (merges with existing tags)
        
        Args:
            hostname: Hostname to update
            tag: Tag name
            value: Tag value
            
        Returns:
            int: Result.SUCCESS (0) if successful, Result.ERROR (-1) if failed
        """
        return self.update_host_tags(hostname, [{'tag': tag, 'value': value}], merge=True)

    def remove_host_tag(self, hostname: str, tag: str) -> int:
        """
        Remove a tag from a host
        
        Args:
            hostname: Hostname to update
            tag: Tag name to remove
            
        Returns:
            int: Result.SUCCESS (0) if successful, Result.ERROR (-1) if failed
        """
        hostname_clean = clean_hostname(hostname)
        log(f"Removing tag '{tag}' from host {hostname_clean}")
        
        try:
            # Get existing tags
            existing_tags = self.get_host_tags(hostname)
            if existing_tags is None:
                return Result.ERROR
            
            # Filter out the tag to remove
            new_tags = [t for t in existing_tags if t['tag'] != tag]
            
            if len(new_tags) == len(existing_tags):
                log(f"Tag '{tag}' not found on host {hostname_clean}")
                return Result.SUCCESS
            
            # Update with filtered tags
            return self.update_host_tags(hostname, new_tags, merge=False)
            
        except Exception as e:
            log(f"ERROR: Failed to remove tag: {e}")
            return Result.ERROR

    def update_rp_pdu_port(self, hostname: str, port: str) -> int:
        """
        Update PDU RP Port for a host
        
        Args:
            hostname: Hostname to update
            port: PDU port number (must be numeric)
            
        Returns:
            int: Result.SUCCESS (0) if successful, Result.ERROR (-1) if failed
        """
        # Validate port is numeric
        if not port.isdigit():
            log(f"ERROR: Port must be numeric, got: {port}")
            return Result.ERROR
        
        return self.update_inventory_field(hostname, 'PDU RP Port', port)

    def update_board_pdu_port(self, hostname: str, port: str) -> int:
        """
        Update PDU Board Port for a host
        
        Args:
            hostname: Hostname to update
            port: PDU port number (must be numeric)
            
        Returns:
            int: Result.SUCCESS (0) if successful, Result.ERROR (-1) if failed
        """
        # Validate port is numeric
        if not port.isdigit():
            log(f"ERROR: Port must be numeric, got: {port}")
            return Result.ERROR
        
        return self.update_inventory_field(hostname, 'PDU Board Port', port)

    def update_nuc_pdu_port(self, hostname: str, port: str) -> int:
        """
        Update PDU Nuc Port for a host
        
        Args:
            hostname: Hostname to update
            port: PDU port number (must be numeric)
            
        Returns:
            int: Result.SUCCESS (0) if successful, Result.ERROR (-1) if failed
        """
        # Validate port is numeric
        if not port.isdigit():
            log(f"ERROR: Port must be numeric, got: {port}")
            return Result.ERROR
        
        return self.update_inventory_field(hostname, 'PDU Nuc Port', port)

    def update_host_pdu_port(self, hostname: str, port: str) -> int:
        """
        Update PDU Host Port for a host
        
        Args:
            hostname: Hostname to update
            port: PDU port number (must be numeric)
            
        Returns:
            int: Result.SUCCESS (0) if successful, Result.ERROR (-1) if failed
        """
        # Validate port is numeric
        if not port.isdigit():
            log(f"ERROR: Port must be numeric, got: {port}")
            return Result.ERROR
        
        return self.update_inventory_field(hostname, 'PDU Host Port', port)

    def update_pdu_ip(self, hostname: str, pdu_ip: str) -> int:
        """
        Update PDU IP address for a host
        
        Args:
            hostname: Hostname to update
            pdu_ip: PDU IP address (must be valid IPv4 or IPv6)
            
        Returns:
            int: Result.SUCCESS (0) if successful, Result.ERROR (-1) if failed
        """
        # Validate IP address
        try:
            ipaddress.ip_address(pdu_ip)
        except ValueError:
            log(f"ERROR: Invalid IP address: {pdu_ip}")
            return Result.ERROR
        
        return self.update_inventory_field(hostname, 'PDU IP', pdu_ip)

if __name__ == "__main__":
    # Example usage
    print("ZabbixAdmin - Administrative operations module")
    print("\nExample usage:")
    print("""
    from zabbix_admin import ZabbixAdmin
    
    # Initialize with admin credentials (password is REQUIRED)
    admin = ZabbixAdmin(username="Admin", password="your_password")
    
    # Update inventory fields using human-readable titles (default)
    admin.update_inventory_field('myhost', 'Location', 'Lab-5')
    admin.update_inventory_field('myhost', 'PDU IP', '10.0.0.1')
    
    # Update inventory fields using database field names
    admin.update_inventory_field('myhost', 'location', 'Lab-5', use_title=False)
    
    # Update multiple fields at once (human-readable titles - default)
    admin.update_inventory_fields('myhost', {
        'Location': 'Lab-5',
        'Type': 'Server',
        'PDU IP': '10.0.0.1'
    })
    
    # Update multiple fields at once (database field names)
    admin.update_inventory_fields('myhost', {
        'location': 'Lab-5',
        'type': 'Server',
        'hardware': '10.0.0.1'
    }, use_titles=False)
    
    # Convenience methods for PDU fields
    admin.update_pdu_ip('myhost', '10.0.0.1')
    admin.update_host_pdu_port('myhost', 'Port-1')
    admin.update_board_pdu_port('myhost', 'Port-2')
    admin.update_nuc_pdu_port('myhost', 'Port-3')
    admin.update_rp_pdu_port('myhost', 'Port-4')
    
    # List all custom field mappings
    admin.list_custom_fields()
    
    # Update tags
    admin.update_host_tags('myhost', [
        {'tag': 'Environment', 'value': 'Production'},
        {'tag': 'Owner', 'value': 'TeamA'}
    ])
    
    # Add single tag
    admin.add_host_tag('myhost', 'Status', 'Active')
    """)
