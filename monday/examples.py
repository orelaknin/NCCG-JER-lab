"""
Example scripts for common Monday.com API operations.

This module demonstrates how to use the MondayClient for typical tasks.
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Add the current directory to Python path so we can import monday_client
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from monday_client import MondayClient, MondayAPIError


def example_list_boards():
    """Example: List all boards in your Monday account."""
    print("=== Listing All Boards ===")
    
    try:
        client = MondayClient()
        boards = client.get_boards(limit=10)
        
        print(f"Found {len(boards)} boards:")
        for board in boards:
            print(f"- {board['name']} (ID: {board['id']}) - {board['state']}")
            
    except MondayAPIError as e:
        print(f"Error: {e}")


def example_get_board_details(board_id: str):
    """Example: Get detailed information about a specific board."""
    print(f"=== Board Details for ID: {board_id} ===")
    
    try:
        client = MondayClient()
        board = client.get_board_by_id(board_id)
        
        if not board:
            print(f"Board with ID {board_id} not found.")
            return
        
        print(f"Board Name: {board['name']}")
        print(f"Description: {board.get('description', 'No description')}")
        print(f"State: {board['state']}")
        print(f"Created: {board['created_at']}")
        
        print(f"\nColumns ({len(board['columns'])}):")
        for column in board['columns']:
            print(f"- {column['title']} ({column['type']}) - ID: {column['id']}")
        
        print(f"\nGroups ({len(board['groups'])}):")
        for group in board['groups']:
            print(f"- {group['title']} - ID: {group['id']}")
        
        print(f"\nItems ({len(board.get('items', []))}):")
        for item in board.get('items', [])[:5]:  # Show first 5 items
            print(f"- {item['name']} - ID: {item['id']}")
            
    except MondayAPIError as e:
        print(f"Error: {e}")


def example_list_items(board_id: str):
    """Example: List all items in a specific board."""
    print(f"=== Items in Board ID: {board_id} ===")
    
    try:
        client = MondayClient()
        items = client.get_items(board_id, limit=20)
        
        print(f"Found {len(items)} items:")
        for item in items:
            print(f"\nItem: {item['name']} (ID: {item['id']})")
            print(f"State: {item['state']}")
            print(f"Group: {item.get('group', {}).get('title', 'No group')}")
            
            # Show column values
            if item.get('column_values'):
                print("Column Values:")
                for col_val in item['column_values'][:3]:  # Show first 3 columns
                    if col_val['text']:
                        column_title = col_val.get('column', {}).get('title', 'Unknown')
                        print(f"  - {column_title}: {col_val['text']}")
                        
    except MondayAPIError as e:
        print(f"Error: {e}")


def example_create_item(board_id: str, item_name: str, group_id: str = None):
    """Example: Create a new item in a board."""
    print(f"=== Creating Item '{item_name}' in Board {board_id} ===")
    
    try:
        client = MondayClient()
        
        # Example column values (adjust based on your board structure)
        column_values = {
            "status": {"label": "Working on it"},  # Status column
            "text": "Created via API",  # Text column
            "date": {"date": datetime.now().strftime("%Y-%m-%d")}  # Date column
        }
        
        new_item = client.create_item(
            board_id=board_id,
            item_name=item_name,
            group_id=group_id,
            column_values=column_values
        )
        
        print(f"Successfully created item!")
        print(f"Item ID: {new_item['id']}")
        print(f"Item Name: {new_item['name']}")
        print(f"State: {new_item['state']}")
        
        return new_item['id']
        
    except MondayAPIError as e:
        print(f"Error creating item: {e}")
        return None


def example_update_item(item_id: str, board_id: str, column_id: str, new_value: str):
    """Example: Update a column value for an item."""
    print(f"=== Updating Item {item_id} Column {column_id} ===")
    
    try:
        client = MondayClient()
        
        updated_item = client.update_item_column_value(
            item_id=item_id,
            board_id=board_id,
            column_id=column_id,
            value=new_value
        )
        
        print(f"Successfully updated item!")
        print(f"Item Name: {updated_item['name']}")
        
        # Show updated column values
        print("Updated Column Values:")
        for col_val in updated_item.get('column_values', []):
            if col_val['text']:
                print(f"  - {col_val['id']}: {col_val['text']}")
                
    except MondayAPIError as e:
        print(f"Error updating item: {e}")


def example_user_info():
    """Example: Get current user information."""
    print("=== Current User Information ===")
    
    try:
        client = MondayClient()
        user_info = client.get_user_info()
        
        print(f"Name: {user_info['name']}")
        print(f"Email: {user_info['email']}")
        print(f"User ID: {user_info['id']}")
        print(f"Admin: {user_info.get('is_admin', False)}")
        print(f"Account: {user_info.get('account', {}).get('name', 'Unknown')}")
        
    except MondayAPIError as e:
        print(f"Error: {e}")


def main():
    """Main function demonstrating various Monday API operations."""
    print("Monday.com API Examples")
    print("=======================")
    
    # Check if API token is configured
    if not os.getenv('MONDAY_API_TOKEN'):
        print("Error: MONDAY_API_TOKEN environment variable not set!")
        print("Please copy .env.example to .env and add your Monday API token.")
        return
    
    # Get user info first
    example_user_info()
    print("\n" + "="*50 + "\n")
    
    # List all boards
    example_list_boards()
    print("\n" + "="*50 + "\n")
    
    # For the following examples, you'll need to replace these with actual IDs from your Monday account
    EXAMPLE_BOARD_ID = "your_board_id_here"
    EXAMPLE_GROUP_ID = "your_group_id_here"
    EXAMPLE_COLUMN_ID = "your_column_id_here"
    
    print(f"To run the remaining examples, update the following variables in the script:")
    print(f"EXAMPLE_BOARD_ID = '{EXAMPLE_BOARD_ID}'")
    print(f"EXAMPLE_GROUP_ID = '{EXAMPLE_GROUP_ID}'")
    print(f"EXAMPLE_COLUMN_ID = '{EXAMPLE_COLUMN_ID}'")
    print("\nYou can find these IDs by running the list_boards example above.")
    
    # Uncomment these once you have valid IDs:
    # example_get_board_details(EXAMPLE_BOARD_ID)
    # example_list_items(EXAMPLE_BOARD_ID)
    # new_item_id = example_create_item(EXAMPLE_BOARD_ID, "Test Item from API", EXAMPLE_GROUP_ID)
    # if new_item_id:
    #     example_update_item(new_item_id, EXAMPLE_BOARD_ID, EXAMPLE_COLUMN_ID, "Updated via API")


if __name__ == "__main__":
    main()