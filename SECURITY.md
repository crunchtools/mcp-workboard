# Security Design Document

This document describes the security architecture of mcp-workboard-crunchtools.

## 1. Threat Model

### 1.1 Assets to Protect

| Asset | Sensitivity | Impact if Compromised |
|-------|-------------|----------------------|
| WorkBoard API Token | Critical | Full account access, data exfiltration |
| User Data | High | PII exposure, privacy violations |
| Goal/OKR Data | High | Strategy disclosure, competitive intelligence |

### 1.2 Threat Actors

| Actor | Capability | Motivation |
|-------|------------|------------|
| Malicious AI Agent | Can craft tool inputs | Data exfiltration, privilege escalation |
| Local Attacker | Access to filesystem | Token theft, configuration tampering |
| Network Attacker | Man-in-the-middle | Token interception (mitigated by TLS) |

### 1.3 Attack Vectors

| Vector | Description | Mitigation |
|--------|-------------|------------|
| **Token Leakage** | Token exposed in logs, errors, or outputs | Never log tokens, scrub from errors |
| **Input Injection** | Malicious user_id or goal_id | Strict input validation with Pydantic |
| **Path Traversal** | Manipulated file paths | No filesystem operations |
| **SSRF** | Redirect API calls to internal services | Hardcoded API base URL |
| **Denial of Service** | Exhaust WorkBoard rate limits | Rate limiting awareness |
| **Privilege Escalation** | Access data beyond token scope | Server validates token scope |
| **Supply Chain** | Compromised dependencies | Automated CVE scanning |

## 2. Security Architecture

### 2.1 Defense in Depth Layers

```
+-------------------------------------------------------------+
| Layer 1: Input Validation                                    |
| - Pydantic models for all tool inputs                       |
| - Positive integer validation for IDs                        |
| - Email validation for user creation                         |
| - Reject unexpected fields (extra="forbid")                  |
+-------------------------------------------------------------+
| Layer 2: Token Handling                                      |
| - Environment variable only (never file, never arg)         |
| - Never log, never include in errors                        |
| - Use httpx with auth header (not in URL)                   |
+-------------------------------------------------------------+
| Layer 3: API Client Hardening                               |
| - Hardcoded base URL (https://www.myworkboard.com/wb/apis/v1)|
| - TLS certificate validation (default in httpx)             |
| - Request timeout enforcement (30s)                          |
| - Response size limits (10MB)                                |
+-------------------------------------------------------------+
| Layer 4: Output Sanitization                                |
| - Redact tokens from any error messages                     |
| - Limit response sizes to prevent memory exhaustion         |
| - Structured errors without internal details                |
+-------------------------------------------------------------+
| Layer 5: Runtime Protection                                 |
| - No filesystem access                                      |
| - No shell execution (subprocess)                           |
| - No dynamic code evaluation (eval/exec)                    |
| - Type-safe with Pydantic                                   |
+-------------------------------------------------------------+
| Layer 6: Supply Chain Security                              |
| - Automated CVE scanning via GitHub Actions                 |
| - Dependabot alerts enabled                                 |
| - Weekly dependency audits                                  |
| - Container built on Hummingbird for minimal CVEs           |
+-------------------------------------------------------------+
```

### 2.2 Token Security

The API token is handled with multiple protections:

```python
from pydantic import SecretStr

class Config:
    def __init__(self):
        token = os.environ.get("WORKBOARD_API_TOKEN")
        if not token:
            raise ConfigurationError("WORKBOARD_API_TOKEN required")
        self._token = SecretStr(token)

    @property
    def token(self) -> str:
        return self._token.get_secret_value()

    def __repr__(self) -> str:
        return "Config(token=***)"
```

### 2.3 Input Validation Rules

All inputs are validated:

- **User IDs**: Must be positive integers
- **Goal IDs**: Must be positive integers
- **Email addresses**: Validated via Pydantic EmailStr
- **String lengths**: Enforced min/max lengths
- **Extra Fields**: Rejected (Pydantic extra="forbid")

### 2.4 Error Handling

Errors are sanitized before being returned:

```python
class WorkBoardApiError(UserError):
    def __init__(self, code: int, message: str):
        token = os.environ.get("WORKBOARD_API_TOKEN", "")
        safe_message = message.replace(token, "***") if token else message
        super().__init__(f"WorkBoard API error {code}: {safe_message}")
```

## 3. Supply Chain Security

### 3.1 Automated CVE Scanning

1. **Weekly Scheduled Scans**: Every Monday at 9 AM UTC via `pip-audit`
2. **PR Checks**: Every pull request is scanned before merge
3. **Automatic Issues**: When CVEs are found, issues are created automatically
4. **Dependabot**: Enabled for automatic security updates

### 3.2 Container Security

Built on **[Hummingbird Python](https://quay.io/repository/hummingbird/python)** for minimal CVE exposure.

## 4. Security Checklist

Before each release:

- [ ] All inputs validated through Pydantic models
- [ ] No token exposure in logs or errors
- [ ] No filesystem operations
- [ ] No shell execution
- [ ] No eval/exec
- [ ] Rate limiting considered
- [ ] Error messages don't leak internals
- [ ] Dependencies scanned for CVEs
- [ ] Container rebuilt with latest Hummingbird base

## 5. Reporting Security Issues

Please report security issues to security@crunchtools.com or open a private security advisory on GitHub.

Do NOT open public issues for security vulnerabilities.
