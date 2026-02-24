# Claude Code Instructions

This is a secure MCP server for WorkBoard OKR and strategy execution platform.

## Quick Start

### Option 1: Using uvx (Recommended)

```bash
claude mcp add mcp-workboard-crunchtools \
    --env WORKBOARD_API_TOKEN=your_token_here \
    -- uvx mcp-workboard-crunchtools
```

### Option 2: Using Container

```bash
claude mcp add mcp-workboard-crunchtools \
    --env WORKBOARD_API_TOKEN=your_token_here \
    -- podman run -i --rm -e WORKBOARD_API_TOKEN quay.io/crunchtools/mcp-workboard
```

### Option 3: Local Development

```bash
cd ~/Projects/crunchtools/mcp-workboard
claude mcp add mcp-workboard-crunchtools \
    --env WORKBOARD_API_TOKEN=your_token_here \
    -- uv run mcp-workboard-crunchtools
```

## Getting a WorkBoard API Token

1. Log in to your WorkBoard instance
2. Navigate to Admin Settings > API Configuration
3. Generate a JWT API token
4. Copy the token and use it as `WORKBOARD_API_TOKEN`

## Available Tools

### User Management (4 tools)
- `workboard_get_user` - Get a user by ID or the current authenticated user
- `workboard_list_users` - List all users (Data-Admin role required)
- `workboard_create_user` - Create a new user (Data-Admin role required)
- `workboard_update_user` - Update an existing user

### Objective Management (4 tools)
- `workboard_get_objectives` - Get objectives associated with a user (API capped at 15)
- `workboard_get_objective_details` - Get details for a specific objective with key results
- `workboard_get_my_objectives` - Get the current user's owned objectives by ID (recommended)
- `workboard_create_objective` - Create a new objective with key results (Data-Admin required)

### Key Result Management (2 tools)
- `workboard_get_my_key_results` - List current user's key results with metric IDs
- `workboard_update_key_result` - Update key result progress (weekly check-ins)

## Example Usage

```
User: Who am I in WorkBoard?
User: List all WorkBoard users
User: Show me objectives for user 12345
User: Get details on objective 67890 for user 12345
User: Show me my objectives (IDs: 2900058, 2900075, 2901770)
User: Show me my key results
User: Update key result 12345 to 75
User: Create an objective called "Increase retention" owned by user@example.com
```

## Development

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint
uv run ruff check src tests

# Type check
uv run mypy src
```
