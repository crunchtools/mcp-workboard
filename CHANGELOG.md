# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/).

Entries prior to 2026-09-19 are back-filled from GitHub Release notes (RT #1484).

## [Unreleased]

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
