# mcp-workboard-crunchtools Constitution

> **Version:** 1.2.0
> **Ratified:** 2026-03-10
> **Status:** Active
> **Inherits:** [crunchtools/constitution](https://github.com/crunchtools/constitution) v1.2.0
> **Profile:** MCP Server

This constitution establishes the core principles, constraints, and workflows that govern all development on mcp-workboard-crunchtools.

---

## I. Core Principles

### 1. Five-Layer Security Model

Every change MUST preserve all five security layers. No exceptions.

**Layer 1 — Token Protection:**
- API credentials stored as `SecretStr` (never logged or exposed)
- Environment-variable-only storage
- Automatic scrubbing from error messages

**Layer 2 — Input Validation:**
- Pydantic models enforce strict data types with `extra="forbid"`
- ID validators reject non-positive integers
- Date format validation, string length limits, email validation

**Layer 3 — API Hardening:**
- Auth via `Bearer` token header (never in URL)
- Hardcoded API base URL (`myworkboard.com`) prevents SSRF
- Mandatory TLS certificate validation
- Request timeouts and response size limits (10MB)

**Layer 4 — Dangerous Operation Prevention:**
- No filesystem access, shell execution, or code evaluation
- No `eval()`/`exec()` functions
- No delete operations exposed
- Tools are pure API wrappers with no side effects

**Layer 5 — Supply Chain Security:**
- Weekly automated CVE scanning via GitHub Actions
- Hummingbird container base images (minimal CVE surface)
- Gourmand AI slop detection gating all PRs

### 2. Two-Layer Tool Architecture

Tools follow a strict two-layer pattern:
- `server.py` — `@mcp.tool()` decorated functions that validate args and delegate
- `tools/*.py` — Pure async functions that call `client.py` HTTP methods

Never put business logic in `server.py`. Never put MCP registration in `tools/*.py`.

### 3. Single-Instance Design

The server targets a single hardcoded WorkBoard instance (`myworkboard.com`). The API base URL is intentionally not configurable to prevent SSRF attacks.

### 4. Three Distribution Channels

Every release MUST be available through all three channels simultaneously:

| Channel | Command | Use Case |
|---------|---------|----------|
| uvx | `uvx mcp-workboard-crunchtools` | Zero-install, Claude Code |
| pip | `pip install mcp-workboard-crunchtools` | Virtual environments |
| Container | `podman run quay.io/crunchtools/mcp-workboard` | Isolated, systemd |

### 5. Three Transport Modes

The server MUST support all three MCP transports:
- **stdio** (default) — spawned per-session by Claude Code
- **SSE** — legacy HTTP transport
- **streamable-http** — production HTTP, systemd-managed containers

### 6. Semantic Versioning

Follow [Semantic Versioning 2.0.0](https://semver.org/) strictly.

**MAJOR** (breaking changes — consumers must update):
- Removed or renamed tools
- Changed tool parameter names or types
- Renamed environment variables
- Changed default behavior of existing tools

**MINOR** (new functionality — backwards compatible):
- New tools added
- New optional parameters on existing tools
- New tool groups

**PATCH** (fixes — no functional change):
- Bug fixes in existing tools
- Test additions or improvements
- Security patches (dependency updates)

**No version bump required** (infrastructure, not shipped):
- CI/CD changes (workflows, gourmand config)
- Documentation (README, CLAUDE.md, SECURITY.md)
- Issue templates, pre-commit config
- Governance files (.specify/)

**Version bump happens at release time, not per-commit.** Multiple commits can accumulate between releases. The version in `pyproject.toml`, `server.py`, and `__init__.py` is bumped when cutting a release tag.

**A GitHub Release MUST be created for every version bump.** The release tag triggers PyPI publishing and container image pushes. Without a GitHub Release, merged code is not distributed.

### 7. AI Code Quality

All code MUST pass Gourmand checks before merge. Zero violations required.

### 8. Commit Standards

AI-assisted commits MUST include the `Co-Authored-By` trailer:
```
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

### 9. License

This repository is licensed under **AGPL-3.0-or-later**. A `LICENSE` file containing the full license text MUST be present in the repository root.

---

## II. Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Language | Python | 3.10+ |
| MCP Framework | FastMCP | Latest |
| HTTP Client | httpx | Latest |
| Validation | Pydantic | v2 |
| Container Base | Hummingbird | Latest |
| Package Manager | uv | Latest |
| Build System | hatchling | Latest |
| Linter | ruff | Latest |
| Type Checker | mypy (strict) | Latest |
| Tests | pytest + pytest-asyncio | Latest |
| Slop Detector | gourmand | Latest |

---

## III. Testing Standards

### Mocked API Tests (MANDATORY)

Every tool MUST have a corresponding mocked test. Tests use `httpx.AsyncClient` mocking — no live API calls, no tokens required in CI.

**Pattern:**
1. Build a mock `httpx.Response` with `_mock_response()` helper
2. Patch `httpx.AsyncClient` via `_patch_client()` context manager
3. Call the tool function directly (not the `_tool` wrapper)
4. Assert response structure and values

**Required test coverage per tool group:**

| Tool Group | Test Pattern | Minimum Assertions |
|------------|-------------|-------------------|
| Each read tool | `test_list_*`, `test_get_*` | Pagination headers, response shape |
| Each write tool | `test_create_*`, `test_update_*` | POST/PUT with correct status codes |
| Each delete tool | `test_delete_*` | 204 No Content handling |
| Error cases | `TestClientErrorHandling` | 401, 404, 429, 204 responses |

**Singleton reset:** The `_reset_client_singleton` autouse fixture resets `client._client` and `config._config` between every test to prevent state leakage.

**Tool count assertion:** `test_tool_count` MUST be updated whenever tools are added or removed. This catches accidental regressions.

### Input Validation Tests

Every Pydantic model in `models.py` MUST have tests in `test_validation.py`:
- Valid minimal input
- Valid full input
- Invalid/rejected inputs (empty strings, too-long values, extra fields)
- Injection prevention (special characters in identifiers)

### Security Tests

- Token sanitization: `WorkBoardApiError` MUST scrub tokens from messages
- ID truncation: `NotFoundError` MUST truncate long identifiers
- Config safety: `repr()` and `str()` MUST never expose the token

---

## IV. Gourmand (AI Slop Detection)

All code MUST pass `gourmand --full .` with **zero violations** before merge. Gourmand is a CI gate in GitHub Actions.

### Configuration

- `gourmand.toml` — Check settings, excluded paths
- `gourmand-exceptions.toml` — Documented exceptions with justifications
- `.gourmand-cache/` — Must be in `.gitignore`

### Exception Policy

Exceptions MUST have documented justifications in `gourmand-exceptions.toml`. Acceptable reasons:
- Standard API patterns (HTTP status codes, pagination params)
- Test-specific patterns (intentional invalid input)
- Framework requirements (CLAUDE.md for Claude Code)

---

## V. Code Quality Gates

Every code change must pass through these gates in order:

1. **Lint** — `uv run ruff check src tests`
2. **Type Check** — `uv run mypy src`
3. **Tests** — `uv run pytest -v` (all passing, mocked httpx)
4. **Gourmand** — `gourmand --full .` (zero violations)
5. **Container Build** — `podman build -f Containerfile .`

### CI Pipeline (GitHub Actions)

| Job | What it does | Gates PRs |
|-----|-------------|-----------|
| test | Lint + mypy + pytest (Python 3.10-3.12) | Yes |
| gourmand | AI slop detection | Yes |
| build-container | Containerfile builds | Yes |
| security | Weekly CVE scan + CodeQL | Scheduled |
| publish | PyPI trusted publishing | On release tag |
| container | Dual push: Quay.io job + GHCR job (dependency chain) | On release tag |

---

## VI. Container Conventions

- Use **Containerfile** (not Dockerfile) as the build file name.
- Base image: **Hummingbird** (`quay.io/hummingbird/*`) for minimal CVE surface.
- Always `dnf clean all` after package installs.
- Required LABELs: `maintainer`, `description`.
- Required OCI labels:
  ```
  org.opencontainers.image.source=https://github.com/crunchtools/mcp-workboard
  org.opencontainers.image.description=MCP server for WorkBoard OKR platform
  org.opencontainers.image.licenses=AGPL-3.0-or-later
  ```

### Dual-Push CI Architecture

Container CI workflows MUST use two separate jobs:

1. **`build-and-push-quay`** — Builds and pushes to Quay.io. Includes Trivy security scan.
2. **`build-and-push-ghcr`** — Builds and pushes to GHCR. Uses `needs: build-and-push-quay` dependency. Gated with `if: github.event_name != 'pull_request'`.

---

## VII. Naming Conventions

| Context | Name |
|---------|------|
| GitHub repo | `crunchtools/mcp-workboard` |
| PyPI package | `mcp-workboard-crunchtools` |
| CLI command | `mcp-workboard-crunchtools` |
| Python module | `mcp_workboard_crunchtools` |
| Container (Quay) | `quay.io/crunchtools/mcp-workboard` |
| Container (GHCR) | `ghcr.io/crunchtools/mcp-workboard` |
| systemd service | `mcp-workboard.service` |
| HTTP port | 8007 |
| License | AGPL-3.0-or-later |

---

## VIII. Development Workflow

### Adding a New Tool

1. Add the async function to the appropriate `tools/*.py` file
2. Export it from `tools/__init__.py`
3. Import it in `server.py` and register with `@mcp.tool()`
4. Add a mocked test in `tests/test_tools.py`
5. Update the tool count in `test_tool_count`
6. Run all five quality gates
7. Update CLAUDE.md tool listing

### Adding a New Tool Group

1. Create `tools/new_group.py` with async functions
2. Add imports and `__all__` entries in `tools/__init__.py`
3. Add `@mcp.tool()` wrappers in `server.py`
4. Add a `TestNewGroupTools` class in `tests/test_tools.py`
5. Run all five quality gates

### Cutting a Release

1. Ensure the version in `pyproject.toml`, `server.py`, and `__init__.py` is bumped
2. Merge all changes to `main`
3. Create a GitHub Release with tag `v{VERSION}` (e.g., `v0.7.0`)
4. The release tag automatically triggers PyPI publishing and container image pushes
5. Verify all three distribution channels are live (uvx, pip, container)

### Specification-Driven Development

Every new feature MUST have a spec file (`.specify/specs/NNN-slug/spec.md`) before implementation begins. Specs are numbered sequentially (001, 002, ...).

**Requires a spec:**
- New tools or tool groups
- New architectural layers or subsystems
- Changes to the defense/security model
- New external service integrations
- Changes that affect multiple modules

**Exempt from spec requirement:**
- Bug fixes
- Dependency updates
- CI/CD and infrastructure changes
- Documentation-only changes
- Constitution amendments (governed by ratification process)
- Single-tool additions that follow an existing, documented pattern

---

## IX. Governance

### spec-kit Framework

This repo includes:
- `.specify/memory/constitution.md` — This document
- `.specify/specs/000-baseline/spec.md` — Tool inventory and architecture spec
- `.specify/templates/` — `plan-template.md` and `spec-template.md`

### Amendment Process

1. Create a PR with proposed changes to this constitution
2. Document rationale in PR description
3. Require maintainer approval
4. Update version number upon merge

### Ratification History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-27 | Initial constitution |
| 1.1.0 | 2026-03-10 | Adopt org constitution v1.2.0: mandatory GitHub Release, release workflow |
| 1.2.0 | 2026-03-10 | Full compliance with org v1.2.0 and MCP Server profile v1.0.0 |
