# FollowUp Boss MCP Server

A secure Model Context Protocol (MCP) server for integrating with the FollowUp Boss CRM API. This server provides tools for managing contacts, notes, tasks, and call logging.

## Features

### Contact Management
- List, search, and filter contacts
- Create new contacts
- Update existing contact information
- Delete contacts

### Activity Tracking
- Create and manage notes
- Task management with due dates
- Call logging with outcomes and notes
- Event tracking for interactions

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -e .
   ```

## Configuration

Set your FollowUp Boss API key as an environment variable:
```bash
export FOLLOWUP_BOSS_API_KEY="your_api_key_here"
```

To get your API key:
1. Login to FollowUp Boss
2. Navigate to Admin ’ API
3. Copy your unique API key

## Usage

Run the MCP server:
```bash
python3 fubmcp.py
```

Then connect to it using an MCP client to access the following tools:

### Available Tools

#### Contact Operations
- `list_people` - List contacts with filtering options
- `get_person` - Get detailed contact information
- `create_person` - Add new contacts
- `update_person` - Update contact details
- `delete_person` - Remove contacts

#### Notes Management
- `list_notes` - View notes with optional person filtering
- `get_note` - Get specific note details
- `create_note` - Add notes to contacts

#### Task Management
- `list_tasks` - List tasks with filtering
- `create_task` - Create new tasks
- `update_task` - Update task status or details

#### Activity Tracking
- `create_event` - Log interactions
- `create_call` - Record phone calls

## Security

This MCP server implements several security best practices:
- API keys stored in environment variables only
- Input validation and sanitization
- HTTPS-only connections
- Error handling without sensitive data exposure
- Request timeouts
- Proper authentication handling

## API Coverage

Currently implements ~25% of the FollowUp Boss API, focusing on core CRM functionality. See `UPDATED_CAPABILITIES.md` for detailed feature status.

## Contributing

See `implementation_plan.md` for the roadmap of planned features.