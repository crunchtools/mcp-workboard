# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/).

Entries prior to 2026-09-19 are back-filled from GitHub Release notes (RT #1484).

## [Unreleased]

## [0.15.0] - 2026-10-20

### Changed

- Container base images pinned to `quay.io/hummingbird/python:3.14*` instead of
  `latest`, which moved to Python 3.15.0 on 2026-10-20 (crunchtools/constitution#66).

## [0.14.1] - 2026-10-17

### Fixed
- `workboard_get_team_objectives_tool` timed out in production: `GET /goal`
  pages of 50 took 9-47s, past the client's 30s timeout. Pages are now 25
  objectives (about 7s), fetched four at a time with a 90s timeout for those
  calls only.

## [0.14.0] - 2026-10-17

### Added
- `workboard_get_team_objectives_tool` returns a team's objectives whose dates
  overlap a YYYY-MM-DD window, past quarters included, for quarterly OKR
  snapshots (#24, #25). The API ignores `goal_team_id` on `GET /goal`,
  `/team/{id}/goal` returns no goals, and the web app's `goalSummary` needs a
  browser session, so the tool pages every objective the caller can see and
  filters by team and date itself. Sub-teams are not included. It takes about
  a minute. Based on Gunnar Hellekson's draft.

### Fixed
- `workboard_get_objectives_tool` stopped after the first page: it trusted
  `totalCount`, which the live API reports per page (13, 14, 1). Paging now
  runs until a short or repeated page.

## [0.13.1] - 2026-10-17

### Fixed
- A failed token refresh now names WorkBoard's OAuth error code, e.g.
  `HTTP 400 (invalid_refresh_token)`, instead of a bare "400 Bad Request", so
  a spent refresh token is told apart from a bad client secret.
- A successful refresh logs the response's key names (never values) and warns
  when no new refresh token came back. Whether WorkBoard rotates refresh
  tokens is still unverified; this is what will settle it.

## [0.13.0] - 2026-10-17

### Added
- `workboard_get_workstream_columns_tool` lists the custom Kanban columns in
  use on a workstream, and `workboard_get_workstream_activities_tool` now
  returns the same `columns` catalog alongside the action items. The API has
  no column endpoint, so columns come from the cards; an empty column does not
  appear. Contributed by Gunnar Hellekson (#23).

## [0.12.0] - 2026-10-17

### Added
- **Server-side OAuth re-authorization.** A server running in a container
  behind a reverse proxy can now be re-authorized with a tool call instead of
  running `login` on a workstation and copying `tokens.json` over. Set
  `WORKBOARD_OAUTH_REDIRECT_URI` to the public HTTPS URL of the server's new
  `/callback` route (and register that URL for the WorkBoard app), then:
  - `workboard_auth_status_tool` reports the auth mode, the token store path,
    whether a token exists, and verifies it with `GET /user`, showing the
    account email.
  - `workboard_auth_start_tool` returns the WorkBoard authorize URL. The user
    approves in a browser, WorkBoard redirects to `/callback`, and the server
    exchanges the code and saves the tokens. The CSRF state is held
    server-side, single-use, and expires after 10 minutes.
  - `workboard_auth_result_tool` reports what happened to the most recent
    redirect.
  The callback page never echoes a credential or the authorization code, and
  escapes WorkBoard's `error` parameter. The CLI `login` is unchanged and still
  listens on `http://localhost:8963/callback`.

### Changed
- Token-refresh failure messages now name `workboard_auth_start_tool` alongside
  `mcp-workboard-crunchtools login`.
- A failed token exchange no longer includes WorkBoard's response body in the
  error message.

## [0.11.2] - 2026-10-17

### Fixed
- **`workboard_list_users_tool` lists the organization, not just the caller.**
  It now sends `include=org_members` on `GET /user`, which the WorkBoard API
  requires to return all users (Data-Admin token). It pages with `limit`
  (default 100) and `offset` (#67).
- **`workboard_list_users_tool` defaults to `scope="team"`.** WorkBoard
  rejects `include=org_members` with a 400 unless the token is Data-Admin, so
  the default now lists members of the caller's teams (`include=team_members`),
  which any account can read. `scope="org"` keeps the whole-organization
  listing for Data-Admin tokens.
- **Integer ID parameters publish `ge=1`.** All `user_id`, `objective_id`,
  `team_id`, `metric_id`, `ws_id` and `activity_id` arguments (read and write
  tools) now reject `0` and negative values in the registered schema, as the
  MCP Server profile (Layer 2) requires.
- **`workboard_get_my_objectives_tool` is annotated `readOnlyHint`.**
  `objective_ids` is now capped at 25 positive IDs; longer lists are rejected.
- `workboard_get_team_members_tool` validates `team_id` before building the
  request path, like `get_team_workstreams`.

## [0.11.1] - 2026-10-10

### Fixed
- **OAuth token store is re-read on every call, not cached for the process
  lifetime.** `TokenStore` loaded the token file once and then served the
  in-memory copy forever, so a token refreshed by another process (the `login`
  CLI, or another instance sharing a mounted store) was ignored until the server
  restarted. A long-running container would keep presenting a stale, rejected
  refresh token and return `Token refresh failed: 400` even right after a fresh
  login. `get_access_token` now reloads the store before checking expiry and
  before refreshing, so an externally refreshed token is picked up without a
  restart.
- **Refreshes are serialized across processes with a file lock.** The WorkBoard
  refresh token is single-use and rotates, so two instances sharing the store
  could refresh at once and invalidate each other. Refresh now runs under an
  exclusive lock on a sibling `.lock` file, with a double-checked reload inside
  the lock so a waiter uses the token a peer just wrote instead of spending its
  own.

## [0.11.0] - 2026-10-10

### Added
- The thirteen tools that only read publish `readOnlyHint: true`:
  `get_user`, `list_users`, `get_teams`, `get_team_members`, `get_objectives`,
  `get_objective_details`, `get_my_key_results`, `get_user_key_results`,
  `get_workstreams`, `get_workstream_activities`, `get_team_workstreams`,
  `list_activities` and `get_activity`. A gateway uses the hint to decide
  whether an invalid optional argument may be dropped or must refuse the call
  (crunchtools/constitution#35).
- Tests pin every registered tool into `READ_ONLY` or `WRITES`, and call each
  read-only tool through the registry to check it sends WorkBoard nothing but
  GET requests.

### Changed
- `workboard_get_my_objectives_tool` stays unannotated. It issues only GETs,
  but one per objective ID, and nothing caps how many IDs a caller passes.
- Inherits constitution v1.22.0; the workflow pins and the pre-commit hook rev
  move with it.

### Fixed
- `FastMCP(version=)` and `uv.lock` said 0.10.0 through the 0.10.1 release; they carry the
  release version again.

## [0.10.1] - 2026-10-09

Live API testing (via the MCP server against the production endpoint) found that
the two create-path features shipped in 0.9.0/0.10.0 never actually worked. Both
are fixed here; both root causes were a mismatch between what the tool sent and
what the WorkBoard API accepts.

### Fixed
- **Key results on create were silently dropped.** `workboard_create_objective_tool`
  sent key results under a `metrics` array using `metric_start`/`metric_type`
  (a unit string like `"Percent"`). The API embeds key results under `goal_metrics`
  with `metric_initial_data` and a numeric `metric_unit` (`1` number / `2` currency
  / `3` percent), and silently discards metrics missing the cadence fields
  (`metric_source_from`, `metric_update_interval`, `metric_counting_type`,
  `metric_progress_type`). The mapping now emits the correct field names, maps
  unit names to codes, and fills sensible cadence defaults. Verified live:
  objectives now create with their key results attached.
- **Individual objective creation always failed.** The flat default permission
  `"internal,team"` is invalid for personal goals, and — despite the API's error
  message listing it — the API also rejects `"internal"` for personal goals.
  The permission default is now type-aware: team → `"internal,team"`,
  individual → `"owner"` (personal goals accept `owner`/`manager`). An explicit
  permission is still passed through unchanged.

## [0.10.0] - 2026-10-07

Live API testing against the fixed WorkBoard endpoint (goal_id 3006602 created
successfully) revealed two defects in the 0.9.0 create path, both fixed here.

### Added
- **`team` parameter on `workboard_create_objective_tool`** — team objectives
  require a team association (`goal_team`); without it the API rejects the call.
  Pass `team=<team id>` (from `workboard_get_teams_tool`). A team objective
  created without a team now fails fast with a clear message instead of a
  confusing API error.

### Fixed
- **Objective `permission` default reverted to `"internal,team"`.** The 0.9.0
  change to `"manager"` was based on an incorrect assumption; the live API
  rejects `"manager"` for team objectives (valid: team/report/internal/any,
  comma-separated) and accepts `"internal,team"`. The original default was
  correct all along.

## [0.9.0] - 2026-10-07

WorkBoard deployed a server-side fix (support ticket 122804715) for the 500 that
had blocked Team-objective creation via the API, so objective creation now works
for both Team and Individual objectives. This release unblocks that path and
aligns the create tool with WorkBoard UI vocabulary.

### Changed
- **`workboard_create_objective_tool`**: the `goal_type` parameter is now
  `objective_type`, accepting `"team"` (default) or `"individual"` (numeric
  `"1"`/`"2"` still accepted) instead of raw API codes.
- **Fixed invalid default**: the objective `permission` default was
  `"internal,team"`, which WorkBoard rejects; it is now `"manager"`.
- **Key results on create** are now a declared `KeyResultInput` model
  (`name`, `start_value`, `target_value`, `unit_type`) instead of a free-form
  dict, satisfying the MCP Server profile's no-free-form-objects rule.
- Key-result output key `metric_id` renamed to `key_result_id`;
  `workboard_update_key_result_tool` now returns a normalized key result instead
  of the raw WorkBoard metric payload.
- Docstrings updated: objective creation is no longer described via raw
  `goal_type`; added the note that the API has no update/delete for objectives
  (UI-only).
- Constitution is now a v1.18.0 manifest: only repo-specific facts remain;
  fleet and profile rules apply by reference.
- Constitution validation is pinned via `.github/workflows/constitution.yml`.
- Dependabot auto-merges GitHub Actions minor and patch updates.

## [0.7.0] - 2026-03-10

Workstreams are team-level work containers that track activities, action items,
pace, health, and priority. Contributors: @ghelleks, @fatherlinux.

### Added
- **Workstream management tools (5 new)**: `workboard_get_workstreams_tool`
  (list accessible team workstreams), `workboard_get_workstream_activities_tool`
  (workstream details with all action items),
  `workboard_get_team_workstreams_tool` (workstreams scoped to a specific team),
  `workboard_create_workstream_tool` (manager required), and
  `workboard_update_workstream_tool` (read-before-write + audit log).
- New validation models: `validate_workstream_id()`, `CreateWorkstreamInput`,
  `UpdateWorkstreamInput`.
- `InvalidWorkstreamIdError` added to the error hierarchy.

### Changed
- Tests: 45 → 71 (7 new tool tests, 19 new validation tests).
- Gourmand compliance maintained (zero violations).

## [0.6.1] - 2026-03-03

Patch release with improvements and fixes.

### Changed
- Code quality improvements.
- Dependency updates.

## [0.5.0] - 2026-02-26

Thanks to @ghelleks for both contributions.

### Added
- Expose the `last_updated` field on key result metrics (#2).
- Expose `objective_id`, `target_date`, and `last_updated` on all OKR objects
  (#3).

## [0.4.0] - 2026-02-24

Covers everything since 0.1.1; the intermediate 0.2.0 and 0.3.0 versions were
never tagged. Full tool count: 10 (up from 6 in 0.1.0).

### Added
- Auto-discover objectives from key results (0.4.0).
- OKR update tools `get_my_key_results` and `update_key_result` (0.3.0).
- `get_my_objectives` tool (0.2.0).
- streamable-http transport support.
- Input validation and audit logging.

### Changed
- Renamed goal tools to OKR terminology.
- Improved tool descriptions for LLM discoverability.
- Merged SECURITY.md and SECURITY_AUDIT.md into a single PM-friendly document.

### Fixed
- Metric-goal field name: use `metric_goal_id` from the WorkBoard API.
- `get_my_objectives` now parses the nested API user response.
- ruff B904: use `raise from` in the validator.

## [0.1.1] - 2026-02-17

No GitHub Release was created for this tag, so no authored release notes exist to
back-fill from.

## [0.1.0] - 2026-02-16

Initial release of the secure MCP server for the WorkBoard OKR and strategy
execution platform. Python + FastMCP + httpx + Pydantic, stdio transport,
Hummingbird container, AGPL-3.0.

### Added
- 6 tools. User Management: `workboard_get_user` (by ID or current authenticated
  user), `workboard_list_users` (Data-Admin role required),
  `workboard_create_user` (Data-Admin role required), `workboard_update_user`.
  Goal Management: `workboard_get_goals` (all goals for a user),
  `workboard_get_goal_details`.
