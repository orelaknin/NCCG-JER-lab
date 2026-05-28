#!/usr/bin/env python3
"""
Quick start script for Monday.com API

This script helps you get started with the Monday API quickly.
It will test your API connection and show basic information about your account.
"""

import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from monday_client import MondayClient, MondayAPIError


def setup_environment():
    """Set up the environment and check for API token."""
    load_dotenv()
    
    api_token = os.getenv('MONDAY_API_TOKEN')
    if not api_token:
        print("❌ Monday API token not found!")
        print("\nTo get started:")
        print("1. Copy .env.example to .env")
        print("2. Get your Monday API token from: https://monday.com/developers/apps")
        print("3. Add your token to the .env file")
        print("\nExample .env file:")
        print("MONDAY_API_TOKEN=your_actual_token_here")
        return False
    
    if api_token == "your_monday_api_token_here":
        print("❌ Please replace 'your_monday_api_token_here' with your actual Monday API token in the .env file")
        return False
    
    print("✅ Monday API token found!")
    return True


def test_connection():
    """Test the API connection and get user info."""
    try:
        print("\n🔄 Testing API connection...")
        client = MondayClient()
        
        # Test with user info
        user_info = client.get_user_info()
        
        print("✅ Connection successful!")
        print(f"\nWelcome, {user_info['name']}!")
        print(f"Email: {user_info['email']}")
        print(f"Account: {user_info.get('account', {}).get('name', 'Unknown')}")
        
        return client
        
    except MondayAPIError as e:
        print(f"❌ Connection failed: {e}")
        return None


def show_boards_summary(client):
    """Show a summary of boards in the account."""
    try:
        print("\n📋 Getting boards summary...")
        boards = client.get_boards(limit=10)
        
        if not boards:
            print("No boards found in your account.")
            return
        
        print(f"\nFound {len(boards)} boards (showing first 10):")
        print("-" * 60)
        
        for i, board in enumerate(boards, 1):
            status_emoji = "🟢" if board['state'] == 'active' else "🔴"
            print(f"{i:2d}. {status_emoji} {board['name']}")
            print(f"     ID: {board['id']} | Type: {board.get('board_kind', 'Unknown')}")
            
            # Show column count
            column_count = len(board.get('columns', []))
            group_count = len(board.get('groups', []))
            print(f"     Columns: {column_count} | Groups: {group_count}")
            print()
        
        return boards
        
    except MondayAPIError as e:
        print(f"❌ Failed to get boards: {e}")
        return []


def interactive_mode(client, boards):
    """Interactive mode for exploring boards."""
    if not boards:
        return
    
    print("\n🎯 Interactive Mode")
    print("Choose a board to explore:")
    
    for i, board in enumerate(boards, 1):
        print(f"{i}. {board['name']}")
    
    try:
        choice = input(f"\nEnter board number (1-{len(boards)}) or 'q' to quit: ").strip()
        
        if choice.lower() == 'q':
            return
        
        board_index = int(choice) - 1
        if 0 <= board_index < len(boards):
            selected_board = boards[board_index]
            explore_board(client, selected_board)
        else:
            print("❌ Invalid board number!")
            
    except (ValueError, KeyboardInterrupt):
        print("\n👋 Goodbye!")


def explore_board(client, board):
    """Explore a specific board in detail."""
    board_id = board['id']
    print(f"\n🔍 Exploring board: {board['name']}")
    
    try:
        # Get detailed board info
        detailed_board = client.get_board_by_id(board_id)
        if not detailed_board:
            print("❌ Could not get board details")
            return
        
        print(f"\nBoard Information:")
        print(f"Name: {detailed_board['name']}")
        print(f"Description: {detailed_board.get('description', 'No description')}")
        print(f"State: {detailed_board['state']}")
        print(f"Workspace ID: {detailed_board.get('workspace_id', 'Unknown')}")
        
        # Show columns
        columns = detailed_board.get('columns', [])
        print(f"\nColumns ({len(columns)}):")
        for col in columns:
            print(f"  - {col['title']} ({col['type']}) - ID: {col['id']}")
        
        # Show groups
        groups = detailed_board.get('groups', [])
        print(f"\nGroups ({len(groups)}):")
        for group in groups:
            print(f"  - {group['title']} - ID: {group['id']}")
        
        # Show some items
        items = client.get_items(board_id, limit=5)
        print(f"\nRecent Items (showing first 5 of {len(items)}):")
        for item in items:
            print(f"  - {item['name']} (ID: {item['id']})")
            
    except MondayAPIError as e:
        print(f"❌ Error exploring board: {e}")


def main():
    """Main function."""
    print("🚀 Monday.com API Quick Start")
    print("=" * 40)
    
    # Check environment setup
    if not setup_environment():
        return
    
    # Test connection
    client = test_connection()
    if not client:
        return
    
    # Show boards
    boards = show_boards_summary(client)
    
    # Interactive mode
    if boards:
        try:
            interactive_mode(client, boards)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
    
    print("\n✨ Quick start completed!")
    print("\nNext steps:")
    print("- Check out examples.py for more detailed examples")
    print("- Read the Monday API documentation: https://developer.monday.com/api-reference/docs")
    print("- Explore the monday_client.py module for available methods")


if __name__ == "__main__":
    main()