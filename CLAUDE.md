# Claude Code Instructions

Secure MCP server for WorkBoard OKR and strategy execution platform. 18 tools across 5 categories.

## Quick Start

```bash
# uvx (recommended)
claude mcp add mcp-workboard \
    --env WORKBOARD_API_TOKEN=your_token_here \
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

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WORKBOARD_API_TOKEN` | Yes* | — | WorkBoard JWT API token |
| `WORKBOARD_API_TOKEN_FILE` | Yes* | — | Path to file containing WorkBoard JWT API token |

\* One of `WORKBOARD_API_TOKEN` or `WORKBOARD_API_TOKEN_FILE` is required. File-based loading is preferred for security.

## Available Tools (18)

| Category | Tools | Operations |
|----------|------:|------------|
| Users | 4 | get, list, create, update |
| Teams | 2 | get teams, get team members |
| Objectives | 4 | get, get details, get my objectives, create |
| Key Results | 3 | get mine, get by user, update |
| Workstreams | 5 | get, get activities, get by team, create, update |

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
uv run pytest -v              # Tests (71 mocked)
gourmand --full .             # AI slop detection (zero violations)
```

Quality gates, testing standards, and architecture: `.specify/memory/constitution.md`
