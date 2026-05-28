"""
Monday.com GraphQL API Client

This module provides a Python client for interacting with the Monday.com GraphQL API.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MondayAPIError(Exception):
    """Custom exception for Monday API errors."""
    pass


class MondayClient:
    """
    A client for interacting with Monday.com's GraphQL API.
    
    This client provides methods for common operations like querying boards,
    creating items, updating columns, and more.
    """
    
    def __init__(self, api_token: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize the Monday client.
        
        Args:
            api_token: Monday.com API token. If not provided, will look for MONDAY_API_TOKEN env var.
            api_url: Monday.com API URL. If not provided, will use default or MONDAY_API_URL env var.
        """
        self.api_token = api_token or os.getenv('MONDAY_API_TOKEN')
        self.api_url = api_url or os.getenv('MONDAY_API_URL', 'https://api.monday.com/v2')
        
        if not self.api_token:
            raise MondayAPIError("Monday API token is required. Set MONDAY_API_TOKEN environment variable or pass api_token parameter.")
        
        self.headers = {
            'Authorization': self.api_token,
            'Content-Type': 'application/json',
            'User-Agent': 'Monday-Python-Client/1.0'
        }
        
        logger.info(f"Monday client initialized with API URL: {self.api_url}")
    
    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the Monday API.
        
        Args:
            query: The GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            The response data from the API
            
        Raises:
            MondayAPIError: If the API request fails or returns an error
        """
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        
        logger.debug(f"Executing query: {query}")
        logger.debug(f"Variables: {variables}")
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for GraphQL errors
            if 'errors' in data:
                error_messages = [error.get('message', 'Unknown error') for error in data['errors']]
                raise MondayAPIError(f"GraphQL errors: {', '.join(error_messages)}")
            
            logger.debug(f"Query executed successfully")
            return data.get('data', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise MondayAPIError(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise MondayAPIError(f"Invalid JSON response: {e}")
    
    def get_boards(self, limit: int = 25, page: int = 1) -> List[Dict[str, Any]]:
        """
        Get all boards from your Monday account.
        
        Args:
            limit: Maximum number of boards to return (default: 25)
            page: Page number for pagination (default: 1)
            
        Returns:
            List of board objects
        """
        query = """
        query GetBoards($limit: Int, $page: Int) {
            boards(limit: $limit, page: $page) {
                id
                name
                description
                state
                board_kind
                updated_at
                board_folder_id
                workspace_id
                owners {
                    id
                    name
                    email
                }
                columns {
                    id
                    title
                    type
                    settings_str
                }
                groups {
                    id
                    title
                    color
                }
            }
        }
        """
        
        variables = {'limit': limit, 'page': page}
        result = self.execute_query(query, variables)
        return result.get('boards', [])
    
    def get_board_by_id(self, board_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific board by ID.
        
        Args:
            board_id: The ID of the board to retrieve
            
        Returns:
            Board object or None if not found
        """
        query = """
        query GetBoard($boardId: ID!) {
            boards(ids: [$boardId]) {
                id
                name
                description
                state
                board_kind
                updated_at
                board_folder_id
                workspace_id
                owners {
                    id
                    name
                    email
                }
                columns {
                    id
                    title
                    type
                    settings_str
                }
                groups {
                    id
                    title
                    color
                }
                items {
                    id
                    name
                    state
                    updated_at
                    column_values {
                        id
                        text
                        value
                    }
                }
            }
        }
        """
        
        variables = {'boardId': board_id}
        result = self.execute_query(query, variables)
        boards = result.get('boards', [])
        return boards[0] if boards else None
    
    def get_items(self, board_id: str, limit: int = 25, page: int = 1) -> List[Dict[str, Any]]:
        """
        Get items from a specific board.
        
        Args:
            board_id: The ID of the board
            limit: Maximum number of items to return (default: 25)
            page: Page number for pagination (default: 1)
            
        Returns:
            List of item objects
        """
        query = """
        query GetItems($boardId: [ID!], $limit: Int, $page: Int) {
            boards(ids: $boardId) {
                items(limit: $limit, page: $page) {
                    id
                    name
                    state
                    updated_at
                    group {
                        id
                        title
                    }
                    column_values {
                        id
                        text
                        value
                        column {
                            id
                            title
                            type
                        }
                    }
                }
            }
        }
        """
        
        variables = {'boardId': [board_id], 'limit': limit, 'page': page}
        result = self.execute_query(query, variables)
        boards = result.get('boards', [])
        return boards[0].get('items', []) if boards else []
    
    def create_item(self, board_id: str, item_name: str, group_id: Optional[str] = None, 
                   column_values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new item in a board.
        
        Args:
            board_id: The ID of the board
            item_name: The name of the new item
            group_id: Optional group ID to add the item to
            column_values: Optional dictionary of column values
            
        Returns:
            Created item object
        """
        mutation = """
        mutation CreateItem($boardId: ID!, $itemName: String!, $groupId: String, $columnValues: JSON) {
            create_item(
                board_id: $boardId, 
                item_name: $itemName, 
                group_id: $groupId,
                column_values: $columnValues
            ) {
                id
                name
                state
                column_values {
                    id
                    text
                    value
                }
            }
        }
        """
        
        variables = {
            'boardId': board_id,
            'itemName': item_name,
            'groupId': group_id,
            'columnValues': json.dumps(column_values) if column_values else None
        }
        
        result = self.execute_query(mutation, variables)
        return result.get('create_item', {})
    
    def update_item_column_value(self, item_id: str, board_id: str, column_id: str, 
                                value: Any) -> Dict[str, Any]:
        """
        Update a column value for an item.
        
        Args:
            item_id: The ID of the item
            board_id: The ID of the board
            column_id: The ID of the column to update
            value: The new value for the column
            
        Returns:
            Updated item object
        """
        mutation = """
        mutation UpdateItemColumnValue($itemId: ID!, $boardId: ID!, $columnId: String!, $value: JSON!) {
            change_column_value(
                item_id: $itemId,
                board_id: $boardId,
                column_id: $columnId,
                value: $value
            ) {
                id
                name
                column_values {
                    id
                    text
                    value
                }
            }
        }
        """
        
        variables = {
            'itemId': item_id,
            'boardId': board_id,
            'columnId': column_id,
            'value': json.dumps(value) if not isinstance(value, str) else value
        }
        
        result = self.execute_query(mutation, variables)
        return result.get('change_column_value', {})
    
    def delete_item(self, item_id: str) -> Dict[str, Any]:
        """
        Delete an item.
        
        Args:
            item_id: The ID of the item to delete
            
        Returns:
            Deletion result
        """
        mutation = """
        mutation DeleteItem($itemId: ID!) {
            delete_item(item_id: $itemId) {
                id
            }
        }
        """
        
        variables = {'itemId': item_id}
        result = self.execute_query(mutation, variables)
        return result.get('delete_item', {})
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        Get information about the current user.
        
        Returns:
            User information
        """
        query = """
        query {
            me {
                id
                name
                email
                photo_original
                is_admin
                created_at
                enabled
                account {
                    id
                    name
                    slug
                }
            }
        }
        """
        
        result = self.execute_query(query)
        return result.get('me', {})