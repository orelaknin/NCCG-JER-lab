# Monday.com GraphQL API Integration

A Python library and example scripts for interacting with the Monday.com GraphQL API. This project provides a clean, easy-to-use interface for common Monday.com operations like managing boards, items, and columns.

## Features

- **Complete API Coverage**: Support for boards, items, columns, users, and more
- **Type Safety**: Full type hints and error handling
- **Easy Authentication**: Simple token-based authentication
- **Comprehensive Examples**: Ready-to-use example scripts
- **Logging Support**: Built-in logging for debugging and monitoring
- **Environment Configuration**: Secure token management with environment variables

## Quick Start

### 1. Installation

```bash
# Clone or download this project
# Navigate to the project directory
cd monday

# Create and activate virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate  # On Windows
# source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

1. Copy the example environment file:
   ```bash
   copy .env.example .env
   ```

2. Get your Monday.com API token:
   - Go to [Monday.com Developer Center](https://monday.com/developers/apps)
   - Create a new app or use an existing one
   - Generate an API token
   - Copy the token

3. Edit the `.env` file and add your token:
   ```env
   MONDAY_API_TOKEN=your_actual_monday_api_token_here
   MONDAY_API_URL=https://api.monday.com/v2
   ```

### 3. Test Your Setup

Run the quick start script to verify everything is working:

```bash
python quick_start.py
```

This script will:
- Test your API connection
- Show your user information
- List your boards
- Provide an interactive mode to explore your data

## Usage Examples

### Basic API Client Usage

```python
from monday_client import MondayClient

# Initialize the client (reads from .env file)
client = MondayClient()

# Or provide token directly
client = MondayClient(api_token="your_token_here")

# Get all boards
boards = client.get_boards()
print(f"Found {len(boards)} boards")

# Get specific board
board = client.get_board_by_id("your_board_id")
print(f"Board: {board['name']}")

# Get items from a board
items = client.get_items("your_board_id")
for item in items:
    print(f"Item: {item['name']}")

# Create a new item
new_item = client.create_item(
    board_id="your_board_id",
    item_name="New Task",
    column_values={
        "status": {"label": "Working on it"},
        "text": "Description here"
    }
)

# Update item column value
client.update_item_column_value(
    item_id=new_item['id'],
    board_id="your_board_id",
    column_id="status_column_id",
    value={"label": "Done"}
)
```

### Running Example Scripts

The project includes several example scripts:

```bash
# Interactive quick start
python quick_start.py

# Comprehensive examples
python examples.py
```

## API Reference

### MondayClient Class

The main client class for interacting with Monday.com API.

#### Initialization

```python
MondayClient(api_token=None, api_url=None)
```

- `api_token`: Your Monday.com API token (optional if set in environment)
- `api_url`: API endpoint URL (optional, defaults to Monday.com v2 API)

#### Methods

##### Board Operations

- `get_boards(limit=25, page=1)` - Get all boards
- `get_board_by_id(board_id)` - Get specific board details

##### Item Operations

- `get_items(board_id, limit=25, page=1)` - Get items from a board
- `create_item(board_id, item_name, group_id=None, column_values=None)` - Create new item
- `update_item_column_value(item_id, board_id, column_id, value)` - Update item column
- `delete_item(item_id)` - Delete an item

##### User Operations

- `get_user_info()` - Get current user information

##### Raw GraphQL

- `execute_query(query, variables=None)` - Execute custom GraphQL query

## Project Structure

```
monday/
├── .github/
│   └── copilot-instructions.md    # Project guidelines for AI assistants
├── .venv/                         # Python virtual environment
├── monday_client.py               # Main API client library
├── examples.py                    # Comprehensive usage examples
├── quick_start.py                 # Interactive quick start script
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── .env                          # Your environment variables (create this)
├── .gitignore                    # Git ignore rules
└── README.md                     # This file
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONDAY_API_TOKEN` | Your Monday.com API token | Required |
| `MONDAY_API_URL` | Monday.com API endpoint | `https://api.monday.com/v2` |

## Column Value Formats

Different column types require different value formats:

### Status Column
```python
{"label": "Working on it"}
```

### Text Column
```python
"Your text here"
```

### Date Column
```python
{"date": "2024-12-25"}
```

### Number Column
```python
42  # or "42"
```

### Person Column
```python
{"personsAndTeams": [{"id": 123456, "kind": "person"}]}
```

### Timeline Column
```python
{"from": "2024-01-01", "to": "2024-01-31"}
```

## Error Handling

The library includes comprehensive error handling:

```python
from monday_client import MondayClient, MondayAPIError

try:
    client = MondayClient()
    boards = client.get_boards()
except MondayAPIError as e:
    print(f"Monday API Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Logging

Enable logging to see detailed API interactions:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or just for the Monday client
logger = logging.getLogger('monday_client')
logger.setLevel(logging.DEBUG)
```

## Rate Limiting

Monday.com has rate limits. The client handles basic error responses, but for high-volume usage, consider implementing additional rate limiting logic.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Security

- Never commit your `.env` file or expose your API token
- Use environment variables for sensitive configuration
- Review the Monday.com API permissions for your token

## Troubleshooting

### Common Issues

1. **"Monday API token is required" Error**
   - Ensure your `.env` file exists and contains `MONDAY_API_TOKEN`
   - Verify the token is correct and not expired

2. **"Import 'requests' could not be resolved" Error**
   - Make sure you've installed dependencies: `pip install -r requirements.txt`
   - Activate your virtual environment

3. **"GraphQL errors" in Response**
   - Check that board IDs, item IDs, and column IDs are correct
   - Verify your API token has sufficient permissions

4. **Connection Timeout**
   - Check your internet connection
   - Verify the API URL is correct

### Getting Help

- [Monday.com API Documentation](https://developer.monday.com/api-reference/docs)
- [Monday.com GraphQL Explorer](https://monday.com/developers/apps)
- [Monday.com Developer Community](https://community.monday.com/c/developers/9)

## License

This project is provided as-is for educational and development purposes. Please review Monday.com's API terms of service for commercial usage.

## Changelog

### Version 1.0.0
- Initial release
- Complete Monday.com GraphQL API client
- Example scripts and documentation
- Environment-based configuration
- Error handling and logging