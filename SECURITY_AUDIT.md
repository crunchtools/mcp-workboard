# Security Audit: mcp-workboard-crunchtools

**Date:** 2026-02-24
**Version:** 0.4.0
**Auditor:** Josui (Claude Code)

## Overview

This document covers the security posture of the mcp-workboard-crunchtools MCP server, which provides read/write access to WorkBoard OKRs (Objectives and Key Results) via 10 tools.

## Tools and Their Risk Profile

| Tool | HTTP Method | Risk Level | Notes |
|------|-------------|------------|-------|
| `workboard_get_user_tool` | GET | Low | Read-only |
| `workboard_list_users_tool` | GET | Low | Read-only, requires Data-Admin |
| `workboard_create_user_tool` | POST | Medium | Creates users, requires Data-Admin |
| `workboard_update_user_tool` | PUT | Medium | Modifies user records |
| `workboard_get_objectives_tool` | GET | Low | Read-only, capped at 15 results |
| `workboard_get_objective_details_tool` | GET | Low | Read-only |
| `workboard_get_my_objectives_tool` | GET | Low | Read-only |
| `workboard_get_my_key_results_tool` | GET | Low | Read-only |
| `workboard_update_key_result_tool` | PUT | High | Can modify OKR progress values |
| `workboard_create_objective_tool` | POST | Medium | Creates objectives, requires Data-Admin |

## Security Controls in Place

### Network and Transport
- **SSRF prevention:** Base URL hardcoded to `https://www.myworkboard.com/wb/apis` (`config.py:48-54`). Not configurable.
- **TLS enforced:** `verify=True` on httpx client (`client.py:55`).
- **Request timeouts:** 30-second timeout (`client.py:26,54`).
- **Response size limits:** 10MB cap checked against actual body bytes (`client.py:23,104-108`).

### Authentication and Secrets
- **Token stored as SecretStr:** Prevents accidental logging (`config.py:37`).
- **Token sanitized from error messages:** `WorkBoardApiError` strips token from output (`errors.py:79-81`).
- **Safe repr/str on Config:** Never exposes token (`config.py:56-62`).

### Input Validation
- **ID validation:** All user, objective, and metric IDs validated as positive integers (`models.py:14-34`).
- **User create/update:** Pydantic models with length limits, email validation, `extra="forbid"` (`models.py:37-75`).
- **Key result update:** Pydantic model validates value is a non-negative number (max 20 chars), comment max 1000 chars (`models.py:82-107`).
- **Objective creation:** Pydantic model validates name (max 500), date format (YYYY-MM-DD), goal_type enum, narrative (max 2000), permission (max 100) (`models.py:110-154`).

### Write Operation Safeguards
- **Read-back-before-write:** `update_key_result` fetches the current value before writing and returns a warning if the new value is lower than the current value (`objectives.py:363-387`).
- **Audit logging:** All write operations (`update_key_result`, `create_objective`) emit `AUDIT:` log entries with operation details (`objectives.py:387,395-400,464-470`).
- **Decrease detection:** Value decreases are logged at WARNING level with metric name and ID (`objectives.py:387`).

### Destructive Operations
- **No delete tools exposed.** The HTTP client has a `.delete()` method (`client.py:185-187`), but no tool calls it.
- **Comments cannot be deleted.** The `comment` parameter in `update_key_result` only adds comments via `metric_comment` in the PUT payload. The WorkBoard API's `PUT /metric/{id}` endpoint sets comments alongside data values. There is no delete-comment API path, and no tool invokes `client.delete()`.

## Remaining Risks

### Low Severity

| Risk | Location | Mitigation |
|------|----------|------------|
| `key_results` list in `create_objective` not Pydantic-validated | `objectives.py:457-458` | Requires Data-Admin token; API-side validation |
| `client.delete()` method exists in code | `client.py:185-187` | No tool calls it; code review on new tools |
| Data-Admin tools rely solely on API token scope | `server.py:81-103,257-297` | MCP cannot introspect token scopes; API rejects unauthorized calls |
| Read-back guard adds an extra API call per update | `objectives.py:366-376` | Fails gracefully; performance trade-off, not a security gap |

### Prompt Injection Scenario

The highest-impact attack vector: a prompt injection causes an AI agent to call `update_key_result_tool` with `value: "0"` across all metric IDs discovered via `get_my_key_results_tool`. This is a two-tool chain that could zero out OKR progress.

**Current mitigations:**
- Value must be a non-negative number (can't inject arbitrary strings)
- Read-back guard returns a warning on every decrease
- Audit log captures every update with old/new values
- The attack is detectable and reversible (values can be set back)

**Not mitigated:**
- No hard block on decreases (allowed by design for legitimate corrections)
- No rate limiting at the MCP level (relies on WorkBoard API rate limits)
- No confirmation step before writes

## Change Log

| Date | Change |
|------|--------|
| 2026-02-24 | Initial audit. Added Pydantic validation for `update_key_result` and `create_objective`. Added read-back-before-write guard. Fixed response size check to use actual body bytes. Added audit logging for all write operations. |
