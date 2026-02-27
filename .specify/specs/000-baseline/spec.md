# Specification: Baseline

> **Spec ID:** 000-baseline
> **Status:** Implemented
> **Version:** 0.6.0
> **Author:** crunchtools.com
> **Date:** 2026-02-27

## Overview

Baseline specification for mcp-workboard-crunchtools v0.6.0, documenting all 13 tools across 4 categories that provide secure access to the WorkBoard OKR and strategy execution platform API.

---

## Tools (13)

### User Tools (4)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `get_user` | GET | `/user` or `/user/{id}` | Get current user or specific user by ID |
| `list_users` | GET | `/user` | List all users (Data-Admin required) |
| `create_user` | POST | `/user` | Create a new user (Data-Admin required) |
| `update_user` | PUT | `/user/{id}` | Update an existing user |

### Team Tools (2)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `get_teams` | GET | `/team` | Get all teams the authenticated user belongs to |
| `get_team_members` | GET | `/team/{id}/user` | Get all members of a specific team |

### Objective Tools (4)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `get_objectives` | GET | `/user/{id}/goal` | Get objectives associated with a user (capped at 15) |
| `get_objective_details` | GET | `/user/{id}/goal/{goal_id}` | Get single objective with key results |
| `get_my_objectives` | GET | `/user` + `/metric` + `/user/{id}/goal/{id}` | Auto-discover current user's objectives |
| `create_objective` | POST | `/goal` | Create objective with optional key results (Data-Admin) |

### Key Result Tools (3)

| Tool | Method | Endpoint | Description |
|------|--------|----------|-------------|
| `get_my_key_results` | GET | `/metric` | List current user's key results with metric IDs |
| `get_user_key_results` | GET | `/user/{id}/metric` | List key results for a specific user |
| `update_key_result` | PUT | `/metric/{id}` | Update key result progress (weekly check-ins) |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WORKBOARD_API_TOKEN` | Yes | — | WorkBoard JWT API token |

---

## Error Hierarchy

```
UserError
├── ConfigurationError
├── InvalidUserIdError
├── InvalidObjectiveIdError
├── InvalidMetricIdError
├── NotFoundError
├── PermissionDeniedError
├── RateLimitError
├── WorkBoardApiError
└── ValidationError
```

---

## Module Structure

```
src/mcp_workboard_crunchtools/
├── __init__.py          # Entry point, version, CLI args
├── __main__.py          # python -m support
├── server.py            # FastMCP server, @mcp.tool() wrappers
├── client.py            # httpx async client, error dispatch
├── config.py            # SecretStr token, hardcoded base URL
├── errors.py            # UserError hierarchy
├── models.py            # Pydantic input validation models
└── tools/
    ├── __init__.py      # Re-exports all 13 tool functions
    ├── users.py         # get_user, list_users, create_user, update_user
    ├── teams.py         # get_teams, get_team_members
    └── objectives.py    # get_objectives, get_objective_details, get_my_objectives,
                         # get_my_key_results, get_user_key_results,
                         # update_key_result, create_objective
```

---

## Test Coverage

| Test File | Tests | What It Covers |
|-----------|------:|----------------|
| `test_tools.py` | 25 | Registration, imports, tool count, error safety, config safety, mocked API (users, teams, objectives, key results), error handling (401, 403, 429) |
| `test_validation.py` | 20 | User ID, objective ID, metric ID validation; CreateUserInput, UpdateUserInput Pydantic models |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.6.0 | 2026-02-27 | Added team tools, per-user key results, target_date enrichment, gourmand compliance, spec-kit |
| 0.5.0 | 2026-02-26 | Added get_user_key_results, get_my_objectives auto-discovery |
| 0.4.0 | 2026-02-24 | Added Pydantic validation, decrease detection, audit logging |
| 0.3.0 | 2026-02-23 | Added create_objective, create_user |
| 0.2.0 | 2026-02-22 | Added key result tools |
| 0.1.0 | 2026-02-21 | Initial release with user and objective tools |
