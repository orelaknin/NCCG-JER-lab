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
    
    def execute_query(self, query, variables=None):
        """Execute a GraphQL query against Monday.com API."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            response = requests.post(self.api_url, json=payload, headers=self.headers)
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
    
    def get_group_items(self, board_id, group_id):
        """Get items for a specific group within a board with pagination."""
        query = """
        query ($board_id: ID!, $group_id: String!, $cursor: String) {
            boards(ids: [$board_id]) {
                id
                name
                columns {
                    id
                    title
                    type
                    settings_str
                }
                groups(ids: [$group_id]) {
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
            variables = {"board_id": board_id, "group_id": group_id, "cursor": cursor}
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
                    logging.info(f"  Fetched page {page_num}: {len(items)} items (total so far: {len(all_items)})")
                
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
        """Format group data for Power BI consumption."""
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
    
    def export_group(self, board_id, group_identifier=None, output_file=None):
        """Export one or more groups from a board to a JSON file."""
        logging.info(f"Getting groups for board ID {board_id}...")
        groups_response = self.get_board_groups(board_id)
        
        if "errors" in groups_response:
            error_messages = [error.get("message", str(error)) for error in groups_response["errors"]]
            raise ValueError(f"API Error: {'; '.join(error_messages)}")
        
        if not groups_response.get("data") or not groups_response["data"].get("boards"):
            raise ValueError(f"Board with ID {board_id} not found or not accessible")
        
        board_data = groups_response["data"]["boards"][0]
        groups = board_data.get("groups", [])
        
        if not groups:
            raise ValueError(f"No groups found in board '{board_data['name']}'")

        group_ids = []
        group_names = []
        group_identifier_list = []
        
        if group_identifier:
            if isinstance(group_identifier, str):
                group_identifier_list = [g.strip() for g in group_identifier.split(",") if g.strip()]
            elif isinstance(group_identifier, list):
                group_identifier_list = group_identifier
        else:
            # Auto-select all groups (for automated runs)
            logging.info(f"Auto-selecting all groups from board '{board_data['name']}':")
            for i, group in enumerate(groups, 1):
                logging.info(f"  {i}. {group['title']} (ID: {group['id']})")
            group_identifier_list = [str(i+1) for i in range(len(groups))]

        for g in group_identifier_list:
            found = False
            if g.isdigit():
                idx = int(g)
                if 1 <= idx <= len(groups):
                    group_ids.append(groups[idx-1]["id"])
                    group_names.append(groups[idx-1]["title"])
                    found = True
            
            if not found:
                for group in groups:
                    if group["id"] == g or group["title"].lower() == g.lower():
                        group_ids.append(group["id"])
                        group_names.append(group["title"])
                        found = True
                        break
            
            if not found:
                logging.warning(f"Group '{g}' not found. Skipping.")

        if not group_ids:
            raise ValueError("No valid groups selected.")

        logging.info(f"Exporting groups: {', '.join(group_names)}")

        all_powerbi_data = []
        for gid, gname in zip(group_ids, group_names):
            group_data = self.get_group_items(board_id, gid)
            group_info = {"id": gid, "title": gname}
            powerbi_data = self.format_group_data_for_powerbi(group_data, group_info)
            all_powerbi_data.extend(powerbi_data)

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_group_names = "_".join([g.replace(" ", "_").replace("/", "_").replace("-", "_") for g in group_names])
            output_file = f"monday_group_export_{board_id}_{safe_group_names}_{timestamp}.json"
        else:
            # Add timestamp before .json extension
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if output_file.endswith('.json'):
                output_file = output_file[:-5] + f"_{timestamp}.json"
            else:
                output_file = f"{output_file}_{timestamp}"

        logging.info(f"Writing group data to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_powerbi_data, f, indent=2, ensure_ascii=False)

        logging.info(f"Group export completed successfully!")
        logging.info(f"Board: {board_data['name']}")
        logging.info(f"Groups: {', '.join(group_names)}")
        logging.info(f"Total rows: {len(all_powerbi_data)}")
        logging.info(f"File: {output_file}")
        logging.info(f"Size: {os.path.getsize(output_file)} bytes")

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
    
    # Try config file path as-is first, then relative to script directory
    config_paths = [
        config_file,
        os.path.join(SCRIPT_DIR, config_file)
    ]
    
    config_file_found = None
    for path in config_paths:
        if os.path.exists(path):
            config_file_found = path
            break
    
    if not config_file_found:
        logging.error(f"Config file '{config_file}' not found in current directory or script directory.")
        logging.error(f"Searched paths: {', '.join(config_paths)}")
        return configs
    
    logging.info(f"Using config file: {config_file_found}")
    
    with open(config_file_found, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse the line
            parts = [p.strip() for p in line.split(',')]
            
            if len(parts) < 2:
                logging.warning(f"Line {line_num} is invalid (expected format: board_id,output_filename). Skipping.")
                continue
            
            board_id = parts[0]
            output_filename = parts[1]
            
            if not board_id or not output_filename:
                logging.warning(f"Line {line_num} has empty values. Skipping.")
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
            logging.error("Please set MONDAY_API_TOKEN in the script.")
            sys.exit(1)
    
    # Read configurations
    configs = read_config_file(config_file)
    
    if not configs:
        logging.warning(f"No valid configurations found in '{config_file}'.")
        return
    
    logging.info(f"Found {len(configs)} configuration(s) to process.\n")
    
    # Initialize exporter
    exporter = MondayExporter(api_token)
    
    # Process each configuration
    for i, (board_id, output_filename) in enumerate(configs, 1):
        logging.info(f"\n{'='*60}")
        logging.info(f"Processing configuration {i}/{len(configs)}")
        logging.info(f"Board ID: {board_id}")
        logging.info(f"Output file: {output_filename}")
        logging.info(f"{'='*60}")
        
        try:
            # Export group (will prompt for group selection)
            result_file = exporter.export_group(
                board_id=board_id,
                group_identifier=None,  # Will prompt user
                output_file=output_filename
            )
            logging.info(f"✓ Successfully exported to: {result_file}")
        except Exception as e:
            logging.error(f"✗ Error exporting board {board_id}: {str(e)}")
            continue
    
    logging.info(f"\n{'='*60}")
    logging.info("All exports completed!")


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
    
    # Setup logging
    log_file = setup_logging()
    logging.info(f"Starting Monday.com export - Log file: {log_file}")
    
    export_from_config(args.config_file, args.token)


if __name__ == "__main__":
    main()
