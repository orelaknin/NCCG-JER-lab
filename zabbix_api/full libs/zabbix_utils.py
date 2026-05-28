"""
Zabbix utility functions
Shared utilities for Zabbix controller modules
"""


def clean_hostname(hostname: str) -> str:
    """
    Remove domain suffixes from hostname
    
    Args:
        hostname: Hostname with or without domain suffix
        
    Returns:
        str: Cleaned hostname without domain suffixes
        
    Example:
        >>> clean_hostname("myhost.iil.intel.com")
        "myhost"
        >>> clean_hostname("myhost.jer.intel.com")
        "myhost"
        >>> clean_hostname("myhost")
        "myhost"
    """
    return hostname.replace(".iil.intel.com", "").replace(".jer.intel.com", "")
