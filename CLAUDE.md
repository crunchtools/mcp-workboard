# Claude Code Instructions

Secure MCP server for WorkBoard OKR and strategy execution platform. 22 tools across 5 categories.

## Quick Start

```bash
# Static token (read-only objectives/KRs)
claude mcp add mcp-workboard \
    --env WORKBOARD_API_TOKEN=your_token_here \
    -- uvx mcp-workboard-crunchtools

# OAuth 2 (full permissions — create objectives, KRs, etc.)
export WORKBOARD_CLIENT_ID=your_client_id
export WORKBOARD_CLIENT_SECRET=your_client_secret
mcp-workboard-crunchtools login   # Opens browser, saves tokens locally
claude mcp add mcp-workboard \
    --env WORKBOARD_CLIENT_ID=$WORKBOARD_CLIENT_ID \
    --env WORKBOARD_CLIENT_SECRET=$WORKBOARD_CLIENT_SECRET \
    -- uvx mcp-workboard-crunchtools

# Container
claude mcp add mcp-workboard \
    --env WORKBOARD_API_TOKEN=your_token_here \
    -- podman run -i --rm -e WORKBOARD_API_TOKEN quay.io/crunchtools/mcp-workboard

# Local development
cd ~/Projects/crunchtools/mcp-workboard
claude mcp add mcp-workboard \
    --env WORKBOARD_API_TOKEN=your_token_here \
    -- uv run mcp-workboard-crunchtools
```

## Authentication

Two auth modes, chosen by which environment variables are set:

**Static JWT Token** — Set `WORKBOARD_API_TOKEN` or `WORKBOARD_API_TOKEN_FILE`. Quick setup but limited permissions (instant tokens have `isSuperUser: false`, blocking objective creation).

**OAuth 2** — Set `WORKBOARD_CLIENT_ID` + `WORKBOARD_CLIENT_SECRET`, then run `mcp-workboard-crunchtools login`. This opens your browser for WorkBoard authorization and saves tokens to `~/.config/mcp-workboard/tokens.json`. OAuth tokens carry your full user permissions. Tokens auto-refresh when expired.

To get OAuth credentials: go to WorkBoard Admin > Custom Integrations > App tab, register an app with redirect URI `http://localhost:8963/callback`.

### Lotor / Remote Deployment

For remote deployments where the MCP server runs in a container:
1. Run `mcp-workboard-crunchtools login` on your local machine
2. Copy `~/.config/mcp-workboard/tokens.json` to the remote host
3. Set `WORKBOARD_TOKEN_STORE_PATH` to point to the token file in the container

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WORKBOARD_API_TOKEN` | Auth* | — | WorkBoard JWT API token (static mode) |
| `WORKBOARD_API_TOKEN_FILE` | Auth* | — | Path to file containing JWT token (static mode) |
| `WORKBOARD_CLIENT_ID` | Auth* | — | OAuth 2 client ID |
| `WORKBOARD_CLIENT_SECRET` | Auth* | — | OAuth 2 client secret |
| `WORKBOARD_TOKEN_STORE_PATH` | No | `~/.config/mcp-workboard/tokens.json` | Override token storage location |

\* One auth method required: either `WORKBOARD_API_TOKEN`/`WORKBOARD_API_TOKEN_FILE` (static), or `WORKBOARD_CLIENT_ID` + `WORKBOARD_CLIENT_SECRET` (OAuth).

## Available Tools (22)

| Category | Tools | Operations |
|----------|------:|------------|
| Users | 4 | get, list, create, update |
| Teams | 2 | get teams, get team members |
| Objectives | 4 | get, get details, get my objectives, create |
| Key Results | 3 | get mine, get by user, update |
| Workstreams | 5 | get, get activities, get by team, create, update |
| Activities | 4 | list, get, create, update |

Full tool inventory with API endpoints: `.specify/specs/000-baseline/spec.md`

## Example Usage

```
Who am I in WorkBoard?
List all WorkBoard users
Show me objectives for user 12345
Get details on objective 67890 for user 12345
Show me my objectives
Show me my key results
Update key result 12345 to 75
Show me my teams
Who is on team 5678?
Show key results for user 99
Create an objective called "Increase retention" owned by user@example.com
Show me my workstreams
Show me the action items for workstream 100
Show workstreams for team 5678
```

## Development

```bash
uv sync --all-extras          # Install dependencies
uv run ruff check src tests   # Lint
uv run mypy src               # Type check
uv run pytest -v              # Tests (123 mocked)
gourmand --full .             # AI slop detection (zero violations)
```

Quality gates, testing standards, and architecture: `.specify/memory/constitution.md`
