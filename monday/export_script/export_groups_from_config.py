#!/usr/bin/env python3
"""
Export Monday.com groups based on configuration from a text file.

Config file format (one entry per line):
board_id,output_filename
"""

import requests
import json
import os
import sys
import re
import logging
from datetime import datetime

# Monday.com API Token - Add your token here
MONDAY_API_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjI4NzY4NTc5NSwiYWFpIjoxMSwidWlkIjozNjYwMTM4OSwiaWFkIjoiMjAyMy0xMC0xMFQxMzoxODo0NS4wMDBaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6NTY3OTYwNCwicmduIjoidXNlMSJ9.sDS8PaaHfm8ST8q7_tDg4L5uwcvjvvK5OP3hl0rA6d0"

# Proxy Configuration - Set to None if not needed
HTTP_PROXY = "http://proxy-dmz.intel.com:916"
HTTPS_PROXY = "http://proxy-dmz.intel.com:916"

# Log folder path - will be created if it doesn't exist
# This creates the folder in the same directory as the script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FOLDER = os.path.join(SCRIPT_DIR, "logs")


def setup_logging():
    """Setup logging to file with timestamp."""
    # Create logs folder if it doesn't exist
    try:
        if not os.path.exists(LOG_FOLDER):
            os.makedirs(LOG_FOLDER)
            print(f"Created log folder: {LOG_FOLDER}")
    except Exception as e:
        print(f"Warning: Could not create log folder {LOG_FOLDER}: {e}")
        print(f"Logs will be saved in current directory")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use LOG_FOLDER if it exists, otherwise use current directory
    if os.path.exists(LOG_FOLDER):
        log_filename = os.path.join(LOG_FOLDER, f"monday_export_{timestamp}.log")
    else:
        log_filename = f"monday_export_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Also print to console
        ]
    )
    
    return log_filename


class MondayExporter:
    def __init__(self, api_token):
        self.api_token = api_token
        self.api_url = "https://api.monday.com/v2"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        # Setup proxy if configured
        self.proxies = {}
        if HTTP_PROXY:
            self.proxies['http'] = HTTP_PROXY
            logging.info(f"Using HTTP proxy: {HTTP_PROXY}")
        if HTTPS_PROXY:
            self.proxies['https'] = HTTPS_PROXY
            logging.info(f"Using HTTPS proxy: {HTTPS_PROXY}")
    
    def execute_query(self, query, variables=None):
        """Execute a GraphQL query against Monday.com API."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=self.headers,
                proxies=self.proxies if self.proxies else None
            )
            response.raise_for_status()
            result = response.json()
            
            if "errors" in result:
                logging.error(f"GraphQL Errors: {result['errors']}")
                
            return result
        except requests.exceptions.RequestException as e:
            logging.error(f"HTTP Request failed: {e}")
            raise
    
    def get_board_groups(self, board_id):
        """Get groups for a specific board."""
        query = """
        query ($board_id: ID!) {
            boards(ids: [$board_id]) {
                id
                name
                groups {
                    id
                    title
                    color
                }
            }
        }
        """
        variables = {"board_id": board_id}
        return self.execute_query(query, variables)
    
    def get_board_items(self, board_id):
        """
        Get all items from all groups within a board with pagination.
        
        Args:
            board_id (str): The Monday.com board ID
        
        Returns:
            dict: Dictionary containing board_info, columns, and all items from all groups
        """
        query = """
        query ($board_id: ID!, $cursor: String) {
            boards(ids: [$board_id]) {
                id
                name
                columns {
                    id
                    title
                    type
                    settings_str
                }
                groups {
                    id
                    title
                    items_page(limit: 100, cursor: $cursor) {
                        cursor
                        items {
                            id
                            name
                            state
                            created_at
                            updated_at
                            group {
                                id
                                title
                            }
                            column_values {
                                id
                                text
                                value
                                type
                                ... on MirrorValue {
                                    display_value
                                }
                                ... on BoardRelationValue {
                                    display_value
                                    linked_item_ids
                                    linked_items {
                                        id
                                        name
                                    }
                                }
                                column {
                                    title
                                }
                            }
                            subitems {
                                id
                                name
                                state
                                created_at
                                updated_at
                                column_values {
                                    id
                                    text
                                    value
                                    type
                                    ... on MirrorValue {
                                        display_value
                                    }
                                    ... on BoardRelationValue {
                                        display_value
                                        linked_item_ids
                                        linked_items {
                                            id
                                            name
                                        }
                                    }
                                    column {
                                        title
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        all_items = []
        columns = []
        board_info = {}
        cursor = None
        page_num = 1
        
        while True:
            variables = {"board_id": board_id, "cursor": cursor}
            response = self.execute_query(query, variables)
            
            if "data" in response and response["data"]["boards"]:
                board_data = response["data"]["boards"][0]
                
                if page_num == 1:
                    board_info = {
                        "id": board_data["id"],
                        "name": board_data["name"]
                    }
                    columns = board_data.get("columns", [])
                
                groups = board_data.get("groups", [])
                if not groups:
                    break
                
                items_page = groups[0].get("items_page", {})
                items = items_page.get("items", [])
                
                if items:
                    all_items.extend(items)
                    print(f"  Fetched page {page_num}: {len(items)} items (total so far: {len(all_items)})")
                
                cursor = items_page.get("cursor")
                if not cursor or not items:
                    break
                
                page_num += 1
            else:
                break
        
        return {
            "board_info": board_info,
            "columns": columns,
            "items": all_items
        }
    
    def format_group_data_for_powerbi(self, group_data, group_info):
        """
        Transform Monday.com data into flat tabular format for Power BI.
        
        Converts nested JSON structure into a list of dictionaries where each
        dictionary represents a row with flattened column values.
        
        Args:
            group_data (dict): Raw data from get_board_items containing items and columns
            group_info: Unused parameter (kept for backwards compatibility)
        
        Returns:
            list: List of dictionaries, each representing a row for Power BI import
        """
        powerbi_data = []
        
        columns = group_data.get("columns", [])
        items = group_data.get("items", [])
        
        column_map = {col["id"]: col["title"] for col in columns}
        
        for item in items:
            row = {
                "item_id": item["id"],
                "item_name": item["name"],
                "item_state": item["state"],
                "item_created_at": item["created_at"],
                "item_updated_at": item["updated_at"],
                "group_id": item.get("group", {}).get("id"),
                "group_name": item.get("group", {}).get("title"),
                "item_type": "main_item"
            }
            
            for col_value in item.get("column_values", []):
                column_title = col_value.get("column", {}).get("title") or column_map.get(col_value["id"], f"Column_{col_value['id']}")
                clean_title = column_title.replace(" ", "_").replace("/", "_").replace("-", "_")
                
                linked_items = col_value.get("linked_items", [])
                if linked_items:
                    text_value = ", ".join([item.get("name", "") for item in linked_items if item.get("name")])
                else:
                    text_value = col_value.get("display_value") or col_value.get("text")
                
                if text_value is None or text_value == "":
                    value_field = col_value.get("value")
                    if value_field:
                        try:
                            if isinstance(value_field, str):
                                value_data = json.loads(value_field) if value_field not in ["", "null", "{}"] else {}
                            else:
                                value_data = value_field
                            
                            if isinstance(value_data, dict):
                                if "linkedPulseIds" in value_data:
                                    linked_ids = value_data.get("linkedPulseIds", [])
                                    if linked_ids and isinstance(linked_ids, list):
                                        text_value = ", ".join([str(lid.get("linkedPulseId", lid)) if isinstance(lid, dict) else str(lid) for lid in linked_ids])
                                elif "mirrored_items" in value_data:
                                    mirrored = value_data.get("mirrored_items", [])
                                    if mirrored:
                                        text_value = ", ".join([str(item.get("name", "")) for item in mirrored if item.get("name")])
                                elif "text" in value_data:
                                    text_value = str(value_data.get("text", ""))
                            elif isinstance(value_data, list):
                                if value_data:
                                    text_value = ", ".join([str(v) for v in value_data])
                            elif isinstance(value_data, (str, int, float)):
                                text_value = str(value_data)
                        except Exception as e:
                            text_value = str(value_field) if value_field not in ["null", "{}"] else ""
                
                row[f"col_{clean_title}"] = text_value if text_value is not None else ""
            
            powerbi_data.append(row)
            
            for subitem in item.get("subitems", []):
                subrow = {
                    "item_id": subitem["id"],
                    "item_name": subitem["name"],
                    "item_state": subitem["state"],
                    "item_created_at": subitem["created_at"],
                    "item_updated_at": subitem["updated_at"],
                    "group_id": item.get("group", {}).get("id"),
                    "group_name": item.get("group", {}).get("title"),
                    "parent_item_id": item["id"],
                    "parent_item_name": item["name"],
                    "item_type": "subitem"
                }
                
                for col_value in subitem.get("column_values", []):
                    column_title = col_value.get("column", {}).get("title") or column_map.get(col_value["id"], f"Column_{col_value['id']}")
                    clean_title = column_title.replace(" ", "_").replace("/", "_").replace("-", "_")
                    
                    linked_items = col_value.get("linked_items", [])
                    if linked_items:
                        text_value = ", ".join([item.get("name", "") for item in linked_items if item.get("name")])
                    else:
                        text_value = col_value.get("display_value") or col_value.get("text")
                    
                    if text_value is None or text_value == "":
                        value_field = col_value.get("value")
                        if value_field:
                            try:
                                if isinstance(value_field, str):
                                    value_data = json.loads(value_field) if value_field not in ["", "null", "{}"] else {}
                                else:
                                    value_data = value_field
                                
                                if isinstance(value_data, dict):
                                    if "linkedPulseIds" in value_data:
                                        linked_ids = value_data.get("linkedPulseIds", [])
                                        if linked_ids and isinstance(linked_ids, list):
                                            text_value = ", ".join([str(lid.get("linkedPulseId", lid)) if isinstance(lid, dict) else str(lid) for lid in linked_ids])
                                    elif "mirrored_items" in value_data:
                                        mirrored = value_data.get("mirrored_items", [])
                                        if mirrored:
                                            text_value = ", ".join([str(item.get("name", "")) for item in mirrored if item.get("name")])
                                    elif "text" in value_data:
                                        text_value = str(value_data.get("text", ""))
                                elif isinstance(value_data, list):
                                    if value_data:
                                        text_value = ", ".join([str(v) for v in value_data])
                                elif isinstance(value_data, (str, int, float)):
                                    text_value = str(value_data)
                            except Exception as e:
                                text_value = str(value_field) if value_field not in ["null", "{}"] else ""
                    
                    subrow[f"col_{clean_title}"] = text_value if text_value is not None else ""
                
                powerbi_data.append(subrow)
        
        return powerbi_data
    
    def export_group(self, board_id, output_file=None):
        """
        Export all groups from a board to a JSON file in Power BI format.
        
        Args:
            board_id (str): The Monday.com board ID to export
            output_file (str, optional): Output filename. If None, auto-generates with timestamp.
        
        Returns:
            str: Path to the exported JSON file
        """
        print(f"Getting groups for board ID {board_id}...")

        # Fetch all groups at once
        group_data = self.get_board_items(board_id)
        all_powerbi_data = self.format_group_data_for_powerbi(group_data, None)

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"monday_group_export_{board_id}_{timestamp}.json"
        else:
            # Add timestamp before .json extension
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if output_file.endswith('.json'):
                output_file = output_file[:-5] + f"_{timestamp}.json"
            else:
                output_file = f"{output_file}_{timestamp}"

        print(f"Writing group data to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_powerbi_data, f, indent=2, ensure_ascii=False)

        print(f"Group export completed successfully!")
        print(f"Total rows: {len(all_powerbi_data)}")
        print(f"File: {output_file}")
        print(f"Size: {os.path.getsize(output_file)} bytes")

        return output_file


def read_config_file(config_file):
    """
    Read configuration from text file.
    
    Expected format:
    board_id,output_filename
    
    Args:
        config_file (str): Path to config file
        
    Returns:
        list: List of tuples (board_id, output_filename)
    """
    configs = []
    
    if not os.path.exists(config_file):
        print(f"Error: Config file '{config_file}' not found.")
        return configs
    
    with open(config_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse the line
            parts = [p.strip() for p in line.split(',')]
            
            if len(parts) < 2:
                print(f"Warning: Line {line_num} is invalid (expected format: board_id,output_filename). Skipping.")
                continue
            
            board_id = parts[0]
            output_filename = parts[1]
            
            if not board_id or not output_filename:
                print(f"Warning: Line {line_num} has empty values. Skipping.")
                continue
            
            configs.append((board_id, output_filename))
    
    return configs


def export_from_config(config_file, api_token=None):
    """
    Export groups based on configuration file.
    
    Args:
        config_file (str): Path to config file
        api_token (str): Monday.com API token (if None, will use MONDAY_API_TOKEN constant)
    """
    # Get API token
    if api_token is None:
        api_token = MONDAY_API_TOKEN
        if not api_token or api_token == "your_token_here":
            print("Error: Please set MONDAY_API_TOKEN in the script.")
            sys.exit(1)
    
    # Read configurations
    configs = read_config_file(config_file)
    
    if not configs:
        print(f"No valid configurations found in '{config_file}'.")
        return
    
    print(f"Found {len(configs)} configuration(s) to process.\n")
    
    # Initialize exporter
    exporter = MondayExporter(api_token)
    
    # Process each configuration
    for i, (board_id, output_filename) in enumerate(configs, 1):
        print(f"\n{'='*60}")
        print(f"Processing configuration {i}/{len(configs)}")
        print(f"Board ID: {board_id}")
        print(f"Output file: {output_filename}")
        print(f"{'='*60}")
        
        try:
            # Export group (will prompt for group selection)
            result_file = exporter.export_group(
                board_id=board_id,
                output_file=output_filename
            )
            print(f"✓ Successfully exported to: {result_file}")
        except Exception as e:
            print(f"✗ Error exporting board {board_id}: {str(e)}")
            continue
    
    print(f"\n{'='*60}")
    print("All exports completed!")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Export Monday.com groups based on configuration file.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Config file format:
  board_id,output_filename
  
Example config.txt:
  # This is a comment
  3852792957,kanban_export.json
  4610339484,project_export.json
  
The script will interactively ask you to select groups for each board.
        """
    )
    
    parser.add_argument(
        'config_file',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--token',
        help='Monday.com API token (overrides MONDAY_API_TOKEN env variable)',
        default=None
    )
    
    args = parser.parse_args()
    
    export_from_config(args.config_file, args.token)


if __name__ == "__main__":
    main()
