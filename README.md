# MCP WorkBoard CrunchTools

A secure MCP (Model Context Protocol) server for WorkBoard OKR and strategy execution platform.

## Overview

This MCP server is designed to be:

- **Secure by default** - Threat modeling, input validation, and token protection
- **No third-party services** - Runs locally via stdio, your API token never leaves your machine
- **Cross-platform** - Works on Linux, macOS, and Windows
- **Automatically updated** - GitHub Actions monitor for CVEs and update dependencies
- **Containerized** - Available at `quay.io/crunchtools/mcp-workboard` built on [Hummingbird Python](https://quay.io/repository/hummingbird/python) base image

## Naming Convention

| Component | Name |
|-----------|------|
| GitHub repo | [crunchtools/mcp-workboard](https://github.com/crunchtools/mcp-workboard) |
| Container | `quay.io/crunchtools/mcp-workboard` |
| Python package (PyPI) | `mcp-workboard-crunchtools` |
| CLI command | `mcp-workboard-crunchtools` |
| Module import | `mcp_workboard_crunchtools` |

## Why Hummingbird?

The container image is built on the [Hummingbird Python base image](https://quay.io/repository/hummingbird/python) from [Project Hummingbird](https://github.com/hummingbird-project), which provides:

- **Minimal CVE exposure** - Built with a minimal package set, dramatically reducing attack surface
- **Regular updates** - Security patches applied promptly
- **Optimized for Python** - Pre-configured with uv package manager
- **Production-ready** - Proper signal handling and non-root user defaults

## Features

### User Management (4 tools)
- `workboard_get_user_tool` - Get a user by ID or the current authenticated user
- `workboard_list_users_tool` - List all users (Data-Admin role required)
- `workboard_create_user_tool` - Create a new user (Data-Admin role required)
- `workboard_update_user_tool` - Update an existing user

### Objective Management (4 tools)
- `workboard_get_objectives_tool` - Get objectives associated with a user (API capped at 15)
- `workboard_get_objective_details_tool` - Get details for a specific objective with key results
- `workboard_get_my_objectives_tool` - Get the current user's owned objectives by ID (recommended)
- `workboard_create_objective_tool` - Create a new objective with key results (Data-Admin required)

### Key Result Management (2 tools)
- `workboard_get_my_key_results_tool` - List current user's key results with metric IDs and progress
- `workboard_update_key_result_tool` - Update key result progress for weekly OKR check-ins

### Workstream Management (6 tools)
- `workboard_get_workstreams_tool` - Get team workstreams accessible to the authenticated user
- `workboard_get_workstream_activities_tool` - Get workstream details with all action items
- `workboard_get_workstream_columns_tool` - List the Kanban columns in use on a workstream
- `workboard_get_team_workstreams_tool` - Get all workstreams belonging to a specific team
- `workboard_create_workstream_tool` - Create a new workstream for a team
- `workboard_update_workstream_tool` - Update workstream properties (name, dates, pace, health, priority)

### Authorization (3 tools)
- `workboard_auth_status_tool` - Report auth mode, token store, and whether the credential works (`GET /user`)
- `workboard_auth_start_tool` - Return the WorkBoard authorize URL for browser approval (OAuth mode)
- `workboard_auth_result_tool` - Report the outcome of the most recent authorization redirect

## Installation

### With uvx (Recommended)

```bash
uvx mcp-workboard-crunchtools
```

### With pip

```bash
pip install mcp-workboard-crunchtools
```

### With Container

```bash
podman run -e WORKBOARD_API_TOKEN=your_token \
    quay.io/crunchtools/mcp-workboard
```

## Configuration

### Getting a WorkBoard API Token

1. Log in to your WorkBoard instance
2. Navigate to Admin Settings > API Configuration
3. Generate a JWT API token
4. Copy the token immediately - store it securely

### Add to Claude Code

```bash
claude mcp add mcp-workboard \
    --env WORKBOARD_API_TOKEN=your_token_here \
    -- uvx mcp-workboard-crunchtools
```

Or for the container version:

```bash
claude mcp add mcp-workboard \
    --env WORKBOARD_API_TOKEN=your_token_here \
    -- podman run -i --rm -e WORKBOARD_API_TOKEN quay.io/crunchtools/mcp-workboard
```

### OAuth on a Server (Container Behind a Reverse Proxy)

In OAuth mode (`WORKBOARD_CLIENT_ID` + `WORKBOARD_CLIENT_SECRET`), a server
reachable over HTTPS can be re-authorized without a shell:

1. Register the public callback URL, e.g. `https://workboard.example.com/callback`,
   as the redirect URI of the WorkBoard app.
2. Run the server with an HTTP transport and set
   `WORKBOARD_OAUTH_REDIRECT_URI` to that same URL. The proxy must route
   `/callback` to the server.
3. Call `workboard_auth_start_tool`, open the URL it returns and approve.
   WorkBoard redirects to `/callback`; the server exchanges the code and saves
   the tokens to the token store. The authorization expires after 10 minutes.
4. Call `workboard_auth_status_tool` to confirm (or `workboard_auth_result_tool`
   to see why it failed).

```bash
podman run -p 8000:8000 \
    -e WORKBOARD_CLIENT_ID -e WORKBOARD_CLIENT_SECRET \
    -e WORKBOARD_OAUTH_REDIRECT_URI=https://workboard.example.com/callback \
    -e WORKBOARD_TOKEN_STORE_PATH=/data/tokens.json -v workboard-tokens:/data:Z \
    quay.io/crunchtools/mcp-workboard --transport streamable-http --host 0.0.0.0
```

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKBOARD_OAUTH_REDIRECT_URI` | unset | Public URL of this server's `/callback` route. Required for `workboard_auth_start_tool`; the CLI `login` ignores it and uses `http://localhost:8963/callback`. |
| `WORKBOARD_TOKEN_STORE_PATH` | `~/.config/mcp-workboard/tokens.json` | Where OAuth tokens are stored |

## Usage Examples

### Get Current User

```
User: Who am I in WorkBoard?
Assistant: [calls workboard_get_user with no args]
```

### List All Users

```
User: List all WorkBoard users
Assistant: [calls workboard_list_users]
```

### Get User Objectives

```
User: Show me objectives for user 12345
Assistant: [calls workboard_get_objectives with user_id=12345]
```

### Get Objective Details

```
User: Get details on objective 67890 for user 12345
Assistant: [calls workboard_get_objective_details with user_id=12345, objective_id=67890]
```

### Get My Objectives

```
User: Show me my objectives (IDs: 2900058, 2900075, 2901770)
Assistant: [calls workboard_get_my_objectives with objective_ids=[2900058, 2900075, 2901770]]
```

### List My Key Results

```
User: Show me my key results
Assistant: [calls workboard_get_my_key_results]
```

### Update Key Result Progress

```
User: Update key result 12345 to 75
Assistant: [calls workboard_update_key_result with metric_id=12345, value="75"]
```

### Create an Objective

```
User: Create an objective called "Increase retention" owned by user@example.com
Assistant: [calls workboard_create_objective with name, owner, dates, and optional key_results]
```

### List Workstreams

```
User: Show me my workstreams
Assistant: [calls workboard_get_workstreams]
```

### Get Workstream Action Items

```
User: Show me the agenda for workstream 4130463
Assistant: [calls workboard_get_workstream_activities with ws_id=4130463]
```

## Security

This server was designed with security as a primary concern. See [SECURITY.md](SECURITY.md) for:

- Threat model and attack vectors
- Defense in depth architecture
- Token handling best practices
- Input validation rules

### Key Security Features

1. **Token Protection**
   - Stored as SecretStr (never accidentally logged)
   - Environment variable only (never in files or args)
   - Sanitized from all error messages

2. **Input Validation**
   - Pydantic models for all inputs
   - Positive integer validation for IDs
   - Email validation for user creation

3. **API Hardening**
   - Hardcoded API base URL (prevents SSRF)
   - TLS certificate validation
   - Request timeouts
   - Response size limits

4. **Automated CVE Scanning**
   - GitHub Actions scan dependencies weekly
   - Automatic issues for security updates
   - Dependabot alerts enabled

## Development

### Setup

```bash
git clone https://github.com/crunchtools/mcp-workboard.git
cd mcp-workboard
uv sync
```

### Run Tests

```bash
uv run pytest
```

### Lint and Type Check

```bash
uv run ruff check src tests
uv run mypy src
```

### Build Container

```bash
podman build -t mcp-workboard .
```

## License

AGPL-3.0-or-later

## Contributing

Contributions welcome! Please read SECURITY.md before submitting security-related changes.

## Links

- [WorkBoard API Documentation](https://www.myworkboard.com/wb/apis/)
- [FastMCP Documentation](https://gofastmcp.com/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [crunchtools.com](https://crunchtools.com)

<!-- mcp-name: io.github.crunchtools/workboard -->
