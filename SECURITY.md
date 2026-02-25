# Security: mcp-workboard-crunchtools

**Last updated:** 2026-02-24
**Version:** 0.4.0

## What This Server Can and Cannot Do

This MCP server gives AI agents read/write access to your WorkBoard OKRs. Before deploying it, you should understand what's at stake and what protections are in place.

**The biggest risk:** An AI agent — whether through a prompt injection attack or a hallucination — could modify your OKR progress values. It could set key results to zero, inflate numbers, or create bogus objectives. The server mitigates this with input validation, decrease detection, and audit logging, but it does not block writes outright because legitimate use requires them.

**What the server can do:**
- Read users, objectives, and key results
- Update key result progress values (including lowering them)
- Add comments to key results
- Create new users and objectives (requires a Data-Admin token)

**What the server cannot do:**
- Delete anything. No delete operations are exposed. Comments, once added, cannot be removed.
- Access other systems. The server only talks to `myworkboard.com` — the destination is hardcoded and cannot be changed.
- Run code, access files, or execute shell commands.

## Risk Summary

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AI agent zeros out OKR progress | Low | High | Decrease detection warns on every drop; audit log records old/new values; values are reversible |
| API token stolen from environment | Low | Critical | Token stored as SecretStr, scrubbed from all error output, never logged |
| Malicious input injected via tool parameters | Low | Medium | All inputs validated through Pydantic models with strict type/length/format rules |
| Sensitive data exposed in error messages | Low | High | Error messages sanitized; token stripped; internal details hidden |
| Oversized API response causes memory exhaustion | Very Low | Medium | 10MB cap enforced on actual response body bytes |
| Supply chain vulnerability in dependencies | Low | High | Weekly automated CVE scanning, Dependabot alerts, Hummingbird container base |

## Tools and Their Risk Levels

Of the 10 tools, 7 are read-only and low-risk. The 3 write tools are where the risk lives:

| Tool | What It Does | Risk | Why |
|------|-------------|------|-----|
| **update_key_result** | Changes OKR progress values | **High** | Can lower or inflate numbers |
| **create_objective** | Creates new objectives | Medium | Requires Data-Admin token |
| **create_user** | Creates new WorkBoard users | Medium | Requires Data-Admin token |

The remaining tools (`get_user`, `list_users`, `update_user`, `get_objectives`, `get_objective_details`, `get_my_objectives`, `get_my_key_results`) are read-only or low-impact updates.

## How Write Operations Are Protected

### Key Result Updates

When an AI agent updates a key result, the server:

1. **Validates the input** — the value must be a non-negative number (no arbitrary strings, no negative values, no injection payloads)
2. **Reads the current value first** — before writing, it fetches the existing progress from WorkBoard
3. **Detects decreases** — if the new value is lower than the current value, a warning is returned to the AI agent and logged
4. **Logs the operation** — every update is recorded with the metric ID, new value, and comment

Comments added to key results are append-only. There is no way to delete or modify a comment after it has been submitted.

### Objective and User Creation

These tools require a Data-Admin API token. If your token does not have Data-Admin scope, these tools will fail with a permission error. Inputs are validated through Pydantic models (name lengths, date formats, email addresses, allowed values).

## Threat Model

### What We're Protecting

| Asset | Sensitivity | What Happens If Compromised |
|-------|-------------|----------------------------|
| WorkBoard API Token | Critical | Full account access, data exfiltration |
| User Data | High | PII exposure, privacy violations |
| OKR Data | High | Strategy disclosure, competitive intelligence |

### Who Might Attack

| Actor | How | What They Want |
|-------|-----|----------------|
| Prompt injection | Crafted input that tricks the AI agent into calling write tools | Sabotage OKR data, exfiltrate strategy info |
| Local attacker | Access to the machine's environment variables | Steal the API token |
| Network attacker | Man-in-the-middle | Intercept the API token (mitigated by TLS) |

### Prompt Injection: The Most Likely Scenario

The most realistic attack: a prompt injection hidden in a document or message causes the AI agent to call `get_my_key_results` (to discover metric IDs) and then `update_key_result` with `value: "0"` for each one. This two-tool chain could zero out all OKR progress.

**Current mitigations:**
- Values must be non-negative numbers (can't inject arbitrary strings)
- The server warns on every decrease and logs it
- The attack is detectable (audit trail) and fully reversible (values can be set back)

**Not mitigated (by design):**
- Decreases are allowed because legitimate corrections need them
- No confirmation dialog before writes — the MCP protocol doesn't support this
- No rate limiting at the MCP level (relies on WorkBoard's own API rate limits)

## Defense in Depth

The server uses six layers of protection:

1. **Input validation** — Pydantic models reject malformed inputs before they reach the API. IDs must be positive integers. Strings have length limits. Dates must match YYYY-MM-DD. Extra/unknown fields are rejected.

2. **Token security** — The API token is loaded from an environment variable, stored as a `SecretStr` (prevents accidental `print()` or logging), and scrubbed from all error messages.

3. **Network hardening** — The API base URL is hardcoded (prevents SSRF). TLS is enforced. Requests time out after 30 seconds. Responses over 10MB are rejected.

4. **Output sanitization** — Error messages never include the API token or internal system details. Response sizes are capped.

5. **Runtime isolation** — No filesystem access, no shell execution, no `eval`/`exec`, no dynamic code loading.

6. **Supply chain security** — Weekly `pip-audit` scans via GitHub Actions. Dependabot enabled. Container built on Hummingbird Python for minimal CVE surface.

## Remaining Low-Severity Gaps

- The `key_results` list parameter in `create_objective` is not Pydantic-validated (relies on API-side validation; requires Data-Admin token to use).
- The HTTP client has a `.delete()` method that no tool currently calls. Any new tool adding delete capability should go through security review.
- Data-Admin tools rely on the API token's scope for authorization — the MCP server cannot inspect token permissions ahead of time.

## Supply Chain Security

1. **Weekly scheduled scans** — Every Monday at 9 AM UTC via `pip-audit` in GitHub Actions
2. **PR checks** — Every pull request is scanned before merge
3. **Automatic issues** — CVE findings create GitHub issues automatically
4. **Dependabot** — Enabled for automatic security updates
5. **Container base** — Built on [Hummingbird Python](https://quay.io/repository/hummingbird/python) for minimal CVE exposure

## Pre-Release Checklist

- [ ] All tool inputs validated through Pydantic models
- [ ] No token exposure in logs or errors
- [ ] No filesystem operations
- [ ] No shell execution or eval/exec
- [ ] Error messages don't leak internals
- [ ] Dependencies scanned for CVEs
- [ ] Container rebuilt with latest Hummingbird base
- [ ] Write operations have audit logging

## Reporting Security Issues

Report security issues to security@crunchtools.com or open a private security advisory on GitHub.

Do NOT open public issues for security vulnerabilities.

## Audit Change Log

| Date | Change |
|------|--------|
| 2026-02-24 | Merged security design doc and audit into single document. Added Pydantic validation for `update_key_result` and `create_objective`. Added read-back-before-write guard with decrease detection. Fixed response size check to use actual body bytes instead of content-length header. Added audit logging for all write operations. Documented comment immutability. |
