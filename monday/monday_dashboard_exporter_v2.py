import requests
import json
import os
from datetime import datetime
import requests
import json
import os
import re

class MondayDashboardExporter:
    def __init__(self, api_token):
        """
        Initialize the Monday.com dashboard exporter.
        
        Args:
            api_token (str): Monday.com API token
        """
        self.api_token = api_token
        self.api_url = "https://api.monday.com/v2"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    def execute_query(self, query, variables=None):
        """
        Execute a GraphQL query against Monday.com API.
        
        Args:
            query (str): GraphQL query string
            variables (dict): Query variables
            
        Returns:
            dict: API response
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            response = requests.post(self.api_url, json=payload, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            
            # Check for GraphQL errors
            if "errors" in result:
                print(f"GraphQL Errors: {result['errors']}")
                
            return result
        except requests.exceptions.RequestException as e:
            print(f"HTTP Request failed: {e}")
            print(f"Response status: {response.status_code if 'response' in locals() else 'N/A'}")
            if 'response' in locals():
                print(f"Response text: {response.text}")
            raise
    
    def extract_board_id_from_url(self, url):
        """
        Extract board ID from Monday.com URL.
        
        Args:
            url (str): Monday.com board URL
            
        Returns:
            str: Board ID or None if not found
        """
        import re
        # Match patterns like:
        # https://company.monday.com/boards/123456789
        # https://company.monday.com/boards/123456789/views/123456
        match = re.search(r'/boards/(\d+)', url)
        return match.group(1) if match else None
    
    def get_board_by_id(self, board_id):
        """Get a specific board by ID."""
        query = """
        query ($board_id: ID!) {
            boards(ids: [$board_id]) {
                id
                name
                description
                state
                board_kind
                workspace {
                    id
                    name
                }
                groups {
                    id
                    title
                    color
                }
                columns {
                    id
                    title
                    type
                    settings_str
                }
            }
        }
        """
        variables = {"board_id": board_id}
        response = self.execute_query(query, variables)
        
        # Debug: Print the full response
        print(f"DEBUG - API Response for board {board_id}:")
        print(json.dumps(response, indent=2))
        
        return response
    
    def get_board_items(self, board_id):
        """Get items for a specific board."""
        query = """
        query ($board_id: ID!) {
            boards(ids: [$board_id]) {
                items_page {
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
                        }
                        subitems {
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
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {"board_id": board_id}
        return self.execute_query(query, variables)
    
    def list_available_boards(self):
        """List all available boards for selection."""
        query = """
        query {
            boards {
                id
                name
                description
                workspace {
                    name
                }
            }
        }
        """
        return self.execute_query(query)
    
    def get_boards(self):
        """Get all boards accessible to the user."""
        query = """
        query {
            boards {
                id
                name
                description
                state
                board_kind
                workspace {
                    id
                    name
                }
                groups {
                    id
                    title
                    color
                }
                columns {
                    id
                    title
                    type
                    settings_str
                }
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
                    }
                }
            }
        }
        """
        return self.execute_query(query)
    
    def get_workspaces(self):
        """Get all workspaces."""
        query = """
        query {
            workspaces {
                id
                name
                description
                state
                created_at
            }
        }
        """
        return self.execute_query(query)
    
    def get_users(self):
        """Get all users in the account."""
        query = """
        query {
            users {
                id
                name
                email
                title
                birthday
                country_code
                is_guest
                is_pending
                created_at
                enabled
            }
        }
        """
        return self.execute_query(query)
    
    def get_teams(self):
        """Get all teams."""
        query = """
        query {
            teams {
                id
                name
                picture_url
                users {
                    id
                    name
                    email
                }
            }
        }
        """
        return self.execute_query(query)
    
    def get_group_items(self, board_id, group_id):
        """Get items for a specific group in a board."""
        query = """
        query ($board_id: ID!) {
            boards(ids: [$board_id]) {
                items_page {
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
                        }
                        subitems {
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
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {"board_id": board_id}
        response = self.execute_query(query, variables)
        
        # Filter items by group_id
        if "data" in response and response["data"]["boards"]:
            all_items = response["data"]["boards"][0].get("items_page", {}).get("items", [])
            group_items = [item for item in all_items if item.get("group", {}).get("id") == group_id]
            return group_items
        return []
    
    def export_group_table(self, board_id, group_id, output_file=None):
        """
        Export a specific group as a clean table format for PowerBI.
        
        Args:
            board_id (str): Board ID
            group_id (str): Group ID
            output_file (str): Output file path
            
        Returns:
            str: Path to the exported file
        """
        print(f"Exporting group {group_id} from board {board_id}...")
        
        # Get board structure to understand columns
        board_response = self.get_board_by_id(board_id)
        if "errors" in board_response or not board_response.get("data", {}).get("boards"):
            raise ValueError(f"Could not access board {board_id}")
        
        board_data = board_response["data"]["boards"][0]
        columns = board_data.get("columns", [])
        groups = board_data.get("groups", [])
        
        # Find the specific group
        selected_group = None
        for group in groups:
            if group["id"] == group_id:
                selected_group = group
                break
        
        if not selected_group:
            raise ValueError(f"Group {group_id} not found in board")
        
        # Get items for this group
        group_items = self.get_group_items(board_id, group_id)
        
        # Prepare table data
        table_data = []
        
        for item in group_items:
            row = {
                "item_id": item["id"],
                "item_name": item["name"],
                "item_state": item["state"],
                "created_at": item["created_at"],
                "updated_at": item["updated_at"],
                "group_id": group_id,
                "group_name": selected_group["title"]
            }
            
            # Add column values
            for column_value in item.get("column_values", []):
                # Find column title
                column_title = "unknown_column"
                for col in columns:
                    if col["id"] == column_value["id"]:
                        column_title = col["title"]
                        break
                
                # Clean the column title for use as field name
                clean_title = re.sub(r'[^\w\s]', '', column_title).replace(' ', '_').lower()
                row[f"col_{clean_title}"] = column_value.get("text", "")
            
            table_data.append(row)
            
            # Include subitems if any
            for subitem in item.get("subitems", []):
                subrow = {
                    "item_id": subitem["id"],
                    "item_name": subitem["name"],
                    "item_state": subitem["state"],
                    "created_at": subitem["created_at"],
                    "updated_at": subitem["updated_at"],
                    "group_id": group_id,
                    "group_name": selected_group["title"],
                    "is_subitem": True,
                    "parent_item_id": item["id"]
                }
                
                # Add subitem column values
                for column_value in subitem.get("column_values", []):
                    column_title = "unknown_column"
                    for col in columns:
                        if col["id"] == column_value["id"]:
                            column_title = col["title"]
                            break
                    
                    clean_title = re.sub(r'[^\w\s]', '', column_title).replace(' ', '_').lower()
                    subrow[f"col_{clean_title}"] = column_value.get("text", "")
                
                table_data.append(subrow)
        
        # Create export data
        export_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "board_id": board_id,
                "board_name": board_data["name"],
                "group_id": group_id,
                "group_name": selected_group["title"],
                "total_items": len(table_data),
                "export_type": "group_table_for_powerbi"
            },
            "table_data": table_data,
            "column_definitions": [
                {"id": col["id"], "title": col["title"], "type": col["type"]} 
                for col in columns
            ]
        }
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_group_name = re.sub(r'[^\w\s]', '', selected_group["title"]).replace(' ', '_')
            output_file = f"monday_group_{safe_group_name}_{timestamp}.json"
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"Group export completed successfully!")
        print(f"Board: {board_data['name']}")
        print(f"Group: {selected_group['title']}")
        print(f"Items: {len(table_data)}")
        print(f"File: {output_file}")
        print(f"Size: {os.path.getsize(output_file)} bytes")
        
        return output_file
    
    def export_group_table_csv(self, board_id, group_id, output_file=None):
        """
        Export a specific group as a CSV table format for PowerBI.
        
        Args:
            board_id (str): Board ID
            group_id (str): Group ID
            output_file (str): Output file path
            
        Returns:
            str: Path to the exported file
        """
        import csv
        
        print(f"Exporting group {group_id} from board {board_id} as CSV...")
        
        # Get board structure to understand columns
        board_response = self.get_board_by_id(board_id)
        if "errors" in board_response or not board_response.get("data", {}).get("boards"):
            raise ValueError(f"Could not access board {board_id}")
        
        board_data = board_response["data"]["boards"][0]
        columns = board_data.get("columns", [])
        groups = board_data.get("groups", [])
        
        # Find the specific group
        selected_group = None
        for group in groups:
            if group["id"] == group_id:
                selected_group = group
                break
        
        if not selected_group:
            raise ValueError(f"Group {group_id} not found in board")
        
        # Get items for this group
        group_items = self.get_group_items(board_id, group_id)
        
        # Prepare CSV headers
        headers = [
            "item_id", "item_name", "item_state", "created_at", "updated_at",
            "group_id", "group_name", "is_subitem", "parent_item_id"
        ]
        
        # Add column headers
        for col in columns:
            clean_title = re.sub(r'[^\w\s]', '', col["title"]).replace(' ', '_').lower()
            headers.append(f"col_{clean_title}")
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_group_name = re.sub(r'[^\w\s]', '', selected_group["title"]).replace(' ', '_')
            output_file = f"monday_group_{safe_group_name}_{timestamp}.csv"
        
        # Write CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for item in group_items:
                row = {
                    "item_id": item["id"],
                    "item_name": item["name"],
                    "item_state": item["state"],
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "group_id": group_id,
                    "group_name": selected_group["title"],
                    "is_subitem": False,
                    "parent_item_id": ""
                }
                
                # Add column values
                for column_value in item.get("column_values", []):
                    column_title = "unknown_column"
                    for col in columns:
                        if col["id"] == column_value["id"]:
                            column_title = col["title"]
                            break
                    
                    clean_title = re.sub(r'[^\w\s]', '', column_title).replace(' ', '_').lower()
                    row[f"col_{clean_title}"] = column_value.get("text", "")
                
                writer.writerow(row)
                
                # Include subitems if any
                for subitem in item.get("subitems", []):
                    subrow = {
                        "item_id": subitem["id"],
                        "item_name": subitem["name"],
                        "item_state": subitem["state"],
                        "created_at": subitem["created_at"],
                        "updated_at": subitem["updated_at"],
                        "group_id": group_id,
                        "group_name": selected_group["title"],
                        "is_subitem": True,
                        "parent_item_id": item["id"]
                    }
                    
                    # Add subitem column values
                    for column_value in subitem.get("column_values", []):
                        column_title = "unknown_column"
                        for col in columns:
                            if col["id"] == column_value["id"]:
                                column_title = col["title"]
                                break
                        
                        clean_title = re.sub(r'[^\w\s]', '', column_title).replace(' ', '_').lower()
                        subrow[f"col_{clean_title}"] = column_value.get("text", "")
                    
                    writer.writerow(subrow)
        
        print(f"CSV Group export completed successfully!")
        print(f"Board: {board_data['name']}")
        print(f"Group: {selected_group['title']}")
        print(f"File: {output_file}")
        print(f"Size: {os.path.getsize(output_file)} bytes")
        
        return output_file
    
    def export_board(self, board_identifier, output_file=None):
        """
        Export a specific board to a JSON file.
        
        Args:
            board_identifier (str): Board ID, name, or URL
            output_file (str): Output file path. If None, generates timestamp-based filename.
            
        Returns:
            str: Path to the exported file
        """
        # Try to extract board ID from URL if it looks like a URL
        board_id = None
        if board_identifier.startswith('http'):
            board_id = self.extract_board_id_from_url(board_identifier)
            if not board_id:
                raise ValueError(f"Could not extract board ID from URL: {board_identifier}")
        elif board_identifier.isdigit():
            # If it's just numbers, treat as board ID
            board_id = board_identifier
        else:
            # If it's not a URL or ID, search by name
            boards_response = self.list_available_boards()
            if "data" in boards_response and boards_response["data"]["boards"]:
                for board in boards_response["data"]["boards"]:
                    if board["name"].lower() == board_identifier.lower():
                        board_id = board["id"]
                        break
                
                if not board_id:
                    # Show available boards
                    available_boards = [(b["id"], b["name"]) for b in boards_response["data"]["boards"]]
                    boards_list = "\n".join([f"  {id}: {name}" for id, name in available_boards])
                    raise ValueError(f"Board '{board_identifier}' not found. Available boards:\n{boards_list}")
            else:
                raise ValueError("No boards found in your account")
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"monday_board_export_{board_id}_{timestamp}.json"
        
        print(f"Exporting board ID {board_id}...")
        
        # Get board data
        board_response = self.get_board_by_id(board_id)
        
        # Check for errors first
        if "errors" in board_response:
            error_messages = [error.get("message", str(error)) for error in board_response["errors"]]
            raise ValueError(f"API Error: {'; '.join(error_messages)}")
        
        if not board_response.get("data") or not board_response["data"].get("boards") or len(board_response["data"]["boards"]) == 0:
            # Try to get more info about why the board is not accessible
            print(f"Board {board_id} not found. Checking your board access...")
            boards_response = self.list_available_boards()
            if "data" in boards_response and boards_response["data"]["boards"]:
                accessible_boards = [(b["id"], b["name"]) for b in boards_response["data"]["boards"]]
                boards_list = "\n".join([f"  {id}: {name}" for id, name in accessible_boards])
                raise ValueError(f"Board with ID {board_id} not found or not accessible. Your accessible boards:\n{boards_list}")
            else:
                raise ValueError(f"Board with ID {board_id} not found and no boards are accessible with this token")
        
        board_data = board_response["data"]["boards"][0]
        
        # Get items separately
        print(f"Fetching items for board {board_id}...")
        items_response = self.get_board_items(board_id)
        
        # Merge items into board data
        if "data" in items_response and items_response["data"]["boards"]:
            items_page = items_response["data"]["boards"][0].get("items_page", {})
            board_data["items"] = items_page.get("items", [])
        else:
            board_data["items"] = []
        
        export_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "api_version": "v2",
                "exporter": "Monday Board Exporter",
                "board_id": board_id
            },
            "board": board_data
        }
        
        # Count items and subitems
        total_items = len(board_data.get("items", []))
        total_subitems = sum(len(item.get("subitems", [])) for item in board_data.get("items", []))
        
        # Write to file
        print(f"Writing board data to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"Board export completed successfully!")
        print(f"Board: {board_data['name']}")
        print(f"Items: {total_items}")
        print(f"Subitems: {total_subitems}")
        print(f"File: {output_file}")
        print(f"Size: {os.path.getsize(output_file)} bytes")
        
        return output_file
        """
        Export complete Monday.com dashboard data to a JSON file.
        
        Args:
            output_file (str): Output file path. If None, generates timestamp-based filename.
            
        Returns:
            str: Path to the exported file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"monday_dashboard_export_{timestamp}.json"
        
        print("Exporting Monday.com dashboard data...")
        
        dashboard_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "api_version": "v2",
                "exporter": "Monday Dashboard Exporter"
            },
            "workspaces": [],
            "boards": [],
            "users": [],
            "teams": []
        }
        
        try:
            # Get workspaces
            print("Fetching workspaces...")
            workspaces_response = self.get_workspaces()
            if "data" in workspaces_response and workspaces_response["data"]["workspaces"]:
                dashboard_data["workspaces"] = workspaces_response["data"]["workspaces"]
                print(f"Found {len(dashboard_data['workspaces'])} workspaces")
            
            # Get boards
            print("Fetching boards and items...")
            boards_response = self.get_boards()
            if "data" in boards_response and boards_response["data"]["boards"]:
                dashboard_data["boards"] = boards_response["data"]["boards"]
                print(f"Found {len(dashboard_data['boards'])} boards")
                
                # Count total items
                total_items = sum(len(board.get("items", [])) for board in dashboard_data["boards"])
                print(f"Found {total_items} total items across all boards")
            
            # Get users
            print("Fetching users...")
            users_response = self.get_users()
            if "data" in users_response and users_response["data"]["users"]:
                dashboard_data["users"] = users_response["data"]["users"]
                print(f"Found {len(dashboard_data['users'])} users")
            
            # Get teams
            print("Fetching teams...")
            teams_response = self.get_teams()
            if "data" in teams_response and teams_response["data"]["teams"]:
                dashboard_data["teams"] = teams_response["data"]["teams"]
                print(f"Found {len(dashboard_data['teams'])} teams")
            
            # Write to file
            print(f"Writing data to {output_file}...")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
            
            print(f"Dashboard export completed successfully!")
            print(f"File: {output_file}")
            print(f"Size: {os.path.getsize(output_file)} bytes")
            
            return output_file
            
        except Exception as e:
            print(f"Error during export: {e}")
            raise

def main():
    """Main function to run the board export."""
    import requests
    import json
    import os
    import re
    
    # Get API token from environment variable or prompt user
    api_token = os.getenv('MONDAY_API_TOKEN')
    
    if not api_token:
        api_token = input("Enter your Monday.com API token: ").strip()
    
    if not api_token:
        print("Error: API token is required")
        return
    
    try:
        # Create exporter instance
        exporter = MondayDashboardExporter(api_token)
        
        # Ask user for export type
        print("\nExport Options:")
        print("1. Export entire board (original functionality)")
        print("2. Export specific group as table for PowerBI")
        
        export_choice = input("\nChoose export type (1-2): ").strip()
        
        if export_choice == "2":
            # Group export workflow
            print("\nBoard Selection for Group Export:")
            print("1. Enter board ID (e.g., 123456789)")
            print("2. Enter board URL (e.g., https://company.monday.com/boards/123456789)")
            print("3. Enter board name (e.g., 'My Project Board')")
            print("4. List all available boards")
            
            choice = input("\nChoose an option (1-4) or enter board identifier directly: ").strip()
            
            if choice == "4":
                # List all boards
                print("\nFetching available boards...")
                boards_response = exporter.list_available_boards()
                if "data" in boards_response and boards_response["data"]["boards"]:
                    print("\nAvailable boards:")
                    for board in boards_response["data"]["boards"]:
                        workspace_name = board.get("workspace", {}).get("name", "Unknown")
                        print(f"  ID: {board['id']} | Name: {board['name']} | Workspace: {workspace_name}")
                    
                    board_identifier = input("\nEnter board ID or name to export: ").strip()
                else:
                    print("No boards found in your account")
                    return
            elif choice in ["1", "2", "3"]:
                board_identifier = input(f"\nEnter board {'ID' if choice == '1' else 'URL' if choice == '2' else 'name'}: ").strip()
            else:
                # Treat the input as board identifier
                board_identifier = choice
            
            if not board_identifier:
                print("Error: Board identifier is required")
                return
            
            # Get board ID
            board_id = None
            if board_identifier.startswith('http'):
                board_id = exporter.extract_board_id_from_url(board_identifier)
                if not board_id:
                    raise ValueError(f"Could not extract board ID from URL: {board_identifier}")
            elif board_identifier.isdigit():
                board_id = board_identifier
            else:
                # Search by name
                boards_response = exporter.list_available_boards()
                if "data" in boards_response and boards_response["data"]["boards"]:
                    for board in boards_response["data"]["boards"]:
                        if board["name"].lower() == board_identifier.lower():
                            board_id = board["id"]
                            break
                    
                    if not board_id:
                        available_boards = [(b["id"], b["name"]) for b in boards_response["data"]["boards"]]
                        boards_list = "\n".join([f"  {id}: {name}" for id, name in available_boards])
                        raise ValueError(f"Board '{board_identifier}' not found. Available boards:\n{boards_list}")
            
            # Get board structure to show groups
            print(f"\nFetching groups for board {board_id}...")
            board_response = exporter.get_board_by_id(board_id)
            
            if "errors" in board_response or not board_response.get("data", {}).get("boards"):
                raise ValueError(f"Could not access board {board_id}")
            
            board_data = board_response["data"]["boards"][0]
            groups = board_data.get("groups", [])
            
            if not groups:
                print("No groups found in this board")
                return
            
            # Show available groups
            print(f"\nAvailable groups in '{board_data['name']}':")
            for i, group in enumerate(groups, 1):
                print(f"  {i}. {group['title']} (ID: {group['id']})")
            
            # Get group selection
            group_choice = input(f"\nSelect group number (1-{len(groups)}) or enter group ID: ").strip()
            
            group_id = None
            if group_choice.isdigit() and 1 <= int(group_choice) <= len(groups):
                group_id = groups[int(group_choice) - 1]["id"]
            else:
                # Check if it's a valid group ID
                for group in groups:
                    if group["id"] == group_choice:
                        group_id = group_choice
                        break
                
                if not group_id:
                    print("Invalid group selection")
                    return
            
            # Ask for output format
            print("\nOutput format:")
            print("1. JSON (default)")
            print("2. CSV (recommended for PowerBI)")
            
            format_choice = input("\nSelect format (1-2) [1]: ").strip()
            if not format_choice:
                format_choice = "1"
            
            # Ask for output file
            if format_choice == "2":
                output_file = input("\nEnter output filename (press Enter for auto-generated .csv): ").strip()
                if not output_file:
                    output_file = None
                
                # Export group as CSV
                exported_file = exporter.export_group_table_csv(board_id, group_id, output_file)
            else:
                output_file = input("\nEnter output filename (press Enter for auto-generated .json): ").strip()
                if not output_file:
                    output_file = None
                
                # Export group as JSON
                exported_file = exporter.export_group_table(board_id, group_id, output_file)
            
            print(f"\nGroup Export Summary:")
            print(f"File: {exported_file}")
            print(f"Status: Success")
            print(f"Ready for PowerBI import!")
            
        else:
            # Original board export workflow
            print("\nBoard Export Options:")
            print("1. Enter board ID (e.g., 123456789)")
            print("2. Enter board URL (e.g., https://company.monday.com/boards/123456789)")
            print("3. Enter board name (e.g., 'My Project Board')")
            print("4. List all available boards")
            
            choice = input("\nChoose an option (1-4) or enter board identifier directly: ").strip()
            
            if choice == "4":
                # List all boards
                print("\nFetching available boards...")
                boards_response = exporter.list_available_boards()
                if "data" in boards_response and boards_response["data"]["boards"]:
                    print("\nAvailable boards:")
                    for board in boards_response["data"]["boards"]:
                        workspace_name = board.get("workspace", {}).get("name", "Unknown")
                        print(f"  ID: {board['id']} | Name: {board['name']} | Workspace: {workspace_name}")
                    
                    board_identifier = input("\nEnter board ID or name to export: ").strip()
                else:
                    print("No boards found in your account")
                    return
            elif choice in ["1", "2", "3"]:
                board_identifier = input(f"\nEnter board {'ID' if choice == '1' else 'URL' if choice == '2' else 'name'}: ").strip()
            else:
                # Treat the input as board identifier
                board_identifier = choice
            
            if not board_identifier:
                print("Error: Board identifier is required")
                return
            
            # Ask for output file
            output_file = input("Enter output filename (press Enter for auto-generated): ").strip()
            if not output_file:
                output_file = None
            
            # Export board
            exported_file = exporter.export_board(board_identifier, output_file)
            
            print(f"\nExport Summary:")
            print(f"File: {exported_file}")
            print(f"Status: Success")
        
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
    except Exception as e:
        print(f"Export Error: {e}")

if __name__ == "__main__":
    main()