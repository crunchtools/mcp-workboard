# mcp-workboard-crunchtools Constitution

> **Version:** 1.3.0
> **Ratified:** 2026-03-10
> **Amended:** 2026-10-02
> **Status:** Active
> **Inherits:** [crunchtools/constitution](https://github.com/crunchtools/constitution) v1.20.0
> **Profile:** MCP Server

This file holds what is specific to mcp-workboard. The fleet rules and the
MCP Server profile (five-layer security model, two-layer tools, distribution
channels, transport modes, quality gates, Gourmand) apply at the inherited
version and are checked against this repo's files by `constitution.yml`. They
are not restated here.

## Security Model Specifics

- **Credentials:** either a static `WORKBOARD_API_TOKEN` (or
  `WORKBOARD_API_TOKEN_FILE`), or OAuth 2 with `WORKBOARD_CLIENT_ID` and
  `WORKBOARD_CLIENT_SECRET`. All are `SecretStr`, never logged, never shown by
  `Config` `repr()`/`str()`, and scrubbed from `WorkBoardApiError` messages.
- **OAuth flow:** authorization code with PKCE. The login callback listens on
  `127.0.0.1:8963` only. Tokens persist at `WORKBOARD_TOKEN_STORE_PATH`
  (default `~/.config/mcp-workboard/tokens.json`), written with mode 0600, and
  are refreshed 60s before expiry.
- **Input limits:** ID validators reject non-positive integers; dates are
  format-validated; strings are length-bounded; emails are validated.
  `NotFoundError` truncates long identifiers.
- **API:** auth travels in a `Bearer` header, never the URL. TLS is always
  validated; responses above 10 MB are rejected and requests time out.
- **No delete tools.** The client has a `delete` method, but no tool exposes
  it.

## Single-Instance Design

The server targets one hardcoded WorkBoard instance,
`https://www.myworkboard.com/wb/apis` (OAuth endpoints under
`https://www.myworkboard.com/wb/oauth/`). The base URL is intentionally not
configurable, to prevent SSRF.

## Instance

| Context | Name |
|---------|------|
| GitHub repo | `crunchtools/mcp-workboard` |
| PyPI package | `mcp-workboard-crunchtools` |
| Python module | `mcp_workboard_crunchtools` |
| Container image | `quay.io/crunchtools/mcp-workboard`, `ghcr.io/crunchtools/mcp-workboard` |
| systemd service | `mcp-workboard.service` |
| HTTP port | 8007 |
| OAuth callback port | 8963 (loopback, login flow only) |

## History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-27 | Initial constitution |
| 1.1.0 | 2026-03-10 | Adopt org constitution v1.2.0: mandatory GitHub Release, release workflow |
| 1.2.0 | 2026-03-10 | Full compliance with org v1.2.0 and MCP Server profile v1.0.0 |
| 1.3.0 | 2026-10-02 | Manifest under constitution v1.18.0: profile restatement removed, mcp-workboard specifics kept |
