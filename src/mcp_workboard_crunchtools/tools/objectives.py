"""Objective management tools.

Tools for retrieving and managing WorkBoard objectives (goals) and their key results.
WorkBoard uses "goal" in its API, but these tools expose OKR terminology.
"""

import asyncio
import contextlib
import logging
from datetime import datetime, timezone
from typing import Any

from ..client import WorkBoardClient, get_client
from ..errors import UserError
from ..models import (
    CreateObjectiveInput,
    KeyResultInput,
    UpdateKeyResultInput,
    metric_unit_code,
    validate_metric_id,
    validate_objective_id,
    validate_user_id,
)

logger = logging.getLogger(__name__)


def _format_date(timestamp: str | int | None) -> str:
    """Convert Unix timestamp to YYYY-MM-DD."""
    if timestamp is None:
        return ""
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        return ""
    if ts <= 0:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _format_metric(
    metric: dict[str, Any],
    target_date_override: str | None = None,
) -> dict[str, Any]:
    """Format a key result metric for human-readable output.

    Args:
        metric: Raw metric dict from WorkBoard API
        target_date_override: Real target date (YYYY-MM-DD) to use instead of the
            value embedded in the nested metric object, which is often absent when
            metrics are returned as part of a goal response.
    """
    unit = metric.get("metric_unit", {})
    unit_name = unit.get("name", "") if isinstance(unit, dict) else ""

    try:
        target = float(metric.get("metric_target") or 0)
    except (ValueError, TypeError):
        target = 0
    try:
        achieved = float(metric.get("metric_achieve_target") or 0)
    except (ValueError, TypeError):
        achieved = 0

    match unit_name:
        case "Currency":
            progress_str = f"${int(achieved):,} of ${int(target):,}"
        case "Number":
            progress_str = f"{int(achieved)} of {int(target)}"
        case _:
            progress_str = f"{int(achieved)}% of {int(target)}%"

    formatted_metric: dict[str, Any] = {
        "key_result_id": int(metric.get("metric_id", 0)),
        "name": metric.get("metric_name", ""),
        "progress": progress_str,
        "target_date": target_date_override or _format_date(metric.get("target_date")),
    }

    raw_last_update = metric.get("metric_last_update")
    try:
        last_update_ts = int(raw_last_update or 0)
    except (ValueError, TypeError):
        last_update_ts = 0

    formatted_metric["last_updated"] = _format_date(last_update_ts) if last_update_ts > 0 else None

    return formatted_metric


def _format_goal(
    goal: dict[str, Any],
    metric_target_dates: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Format an objective for human-readable output.

    Args:
        goal: Raw goal dict from WorkBoard API
        metric_target_dates: Optional {metric_id: "YYYY-MM-DD"} lookup built from
            the /metric endpoint. When provided, used to populate target_date on
            nested key results, which the goal response leaves empty.
    """
    try:
        progress = int(float(goal.get("goal_progress") or 0))
    except (ValueError, TypeError):
        progress = 0

    formatted_goal: dict[str, Any] = {
        "objective_id": goal.get("goal_id"),
        "name": goal.get("goal_name", ""),
        "progress": f"{progress}%",
    }

    owner = goal.get("goal_owner_full_name")
    if owner:
        formatted_goal["owner"] = owner

    owner_id = goal.get("goal_owner")
    if owner_id:
        with contextlib.suppress(ValueError, TypeError):
            formatted_goal["owner_id"] = int(owner_id)

    team = goal.get("goal_team_name")
    if team:
        formatted_goal["team"] = team

    workstreams = goal.get("goal_workstreams")
    if workstreams and isinstance(workstreams, list):
        formatted_goal["workstreams"] = [
            {"id": ws.get("id"), "name": ws.get("name")}
            for ws in workstreams
            if isinstance(ws, dict)
        ]

    status_color = goal.get("goal_progress_color")
    if status_color:
        formatted_goal["status_color"] = status_color

    start = _format_date(goal.get("goal_start_date"))
    target = _format_date(goal.get("goal_target_date"))
    if start and target:
        formatted_goal["dates"] = f"{start} to {target}"

    metrics = goal.get("goal_metrics", [])
    if metrics:
        formatted_goal["key_results"] = [
            _format_metric(
                m,
                target_date_override=(
                    metric_target_dates.get(int(m.get("metric_id", 0)))
                    if metric_target_dates
                    else None
                ),
            )
            for m in metrics
        ]

    return formatted_goal


def _extract_goals_from_goal_response(
    response_body: dict[str, Any],
) -> list[dict[str, Any]]:
    """Normalise data.goal (dict with numeric keys, list of goals, or list of
    user-wrappers with ``people_goals``) into a flat list of goal dicts."""
    goal_data = response_body.get("goal", {})
    match goal_data:
        case dict():
            return [v for k, v in goal_data.items() if k.isdigit() and isinstance(v, dict)]
        case list():
            goals: list[dict[str, Any]] = []
            for item in goal_data:
                if not isinstance(item, dict):
                    continue
                if isinstance(people_goals := item.get("people_goals"), list):
                    goals.extend(g for g in people_goals if isinstance(g, dict))
                elif "goal_id" in item:
                    goals.append(item)
            return goals
        case _:
            return []


def _current_year_start() -> int:
    """Get Unix timestamp for Jan 1 of the current year."""
    now = datetime.now(timezone.utc)
    return int(datetime(now.year, 1, 1, tzinfo=timezone.utc).timestamp())


# The live API honors limit=50 on GET /goal (verified); the 15-result
# cap applied to the old /user/{id}/goal endpoint.
_GOAL_PAGE_SIZE = 50
_GOAL_PAGES_PER_BATCH = 4
_GOAL_MAX_PAGES = 40
_SECONDS_PER_DAY = 86400


async def _fetch_all_goals(client: WorkBoardClient, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Page through ``GET /goal`` until the results run out.

    ``totalCount`` cannot be trusted to stop on: live, it reads 13, 14, then 1
    on successive pages of the same query. Paging stops on a short page or one
    that adds nothing new. The first page is fetched alone, so a query that
    fits in one page costs one request; after that, pages are fetched a batch
    at a time because WorkBoard takes 15-45s per page. Capped at
    ``_GOAL_MAX_PAGES``.
    """
    seen: dict[Any, dict[str, Any]] = {}

    def absorb(response: dict[str, Any]) -> bool:
        """Record a page's goals; True when it shows the results have run out."""
        page = _extract_goals_from_goal_response(response.get("data", {}))
        new = [g for g in page if g.get("goal_id") not in seen]
        seen.update((g.get("goal_id"), g) for g in new)
        return len(page) < _GOAL_PAGE_SIZE or not new

    async def fetch(offset: int) -> dict[str, Any]:
        page_params = {**params, "limit": _GOAL_PAGE_SIZE, "offset": offset}
        return await client.get("/goal", params=page_params)

    if absorb(await fetch(0)):
        return list(seen.values())

    offset = _GOAL_PAGE_SIZE
    while offset < _GOAL_PAGE_SIZE * _GOAL_MAX_PAGES:
        offsets = [offset + i * _GOAL_PAGE_SIZE for i in range(_GOAL_PAGES_PER_BATCH)]
        responses = await asyncio.gather(*(fetch(o) for o in offsets))
        # Absorb every page before deciding: any() would stop at the first.
        exhausted = [absorb(r) for r in responses]
        if any(exhausted):
            break
        offset += _GOAL_PAGE_SIZE * _GOAL_PAGES_PER_BATCH
    return list(seen.values())


def _parse_iso_date(value: str, field: str) -> int:
    """Parse YYYY-MM-DD to a UTC midnight Unix timestamp."""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError) as e:
        raise UserError(f"Invalid {field}. Expected YYYY-MM-DD.") from e
    return int(parsed.timestamp())


def _goal_overlaps(goal: dict[str, Any], start_ts: int, end_ts: int) -> bool:
    """True when the goal's start-to-target span touches [start_ts, end_ts]."""
    try:
        goal_start = int(goal.get("goal_start_date") or 0)
        goal_target = int(goal.get("goal_target_date") or 0)
    except (ValueError, TypeError):
        return False
    return goal_start <= end_ts and goal_target >= start_ts


async def get_team_objectives(
    team_id: int,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Get a team's objectives whose dates overlap a window, past quarters included.

    The API ignores ``goal_team_id`` on ``GET /goal`` and ``/team/{id}/goal``
    returns no goals, so this pages every objective the caller can see and
    filters on ``goal_team_id`` and date overlap here. Sub-teams are not
    included. Expect it to take a minute: WorkBoard is slow per page.

    Args:
        team_id: Team ID (positive integer)
        start_date: Window start, YYYY-MM-DD
        end_date: Window end, YYYY-MM-DD (inclusive)

    Returns:
        Dictionary with the team ID, window, and matching objectives
    """
    if not isinstance(team_id, int) or team_id <= 0:
        raise UserError("Invalid team_id. Expected a positive integer.")
    start_ts = _parse_iso_date(start_date, "start_date")
    end_ts = _parse_iso_date(end_date, "end_date") + _SECONDS_PER_DAY - 1
    if end_ts < start_ts:
        raise UserError("end_date is before start_date.")

    client = get_client()
    all_goals, metric_target_dates = await asyncio.gather(
        _fetch_all_goals(client, {}),
        _fetch_target_date_map(client),
    )

    matching = [
        g
        for g in all_goals
        if str(g.get("goal_team_id")) == str(team_id) and _goal_overlaps(g, start_ts, end_ts)
    ]
    return {
        "team_id": team_id,
        "window": f"{start_date} to {end_date}",
        "objectives": [_format_goal(g, metric_target_dates) for g in matching],
    }


async def get_objectives(
    user_id: int,
) -> dict[str, Any]:
    """Get objectives owned by a WorkBoard user, with full pagination.

    Uses ``GET /goal?goal_owner_id={user_id}`` which supports ``limit``/
    ``offset`` pagination and returns only goals the user owns. Replaces
    the previous ``GET /user/{user_id}/goal`` call which returned at most
    15 results by default and mixed in goals the user was merely associated
    with.

    Args:
        user_id: User ID (positive integer)

    Returns:
        Dictionary containing list of objectives
    """
    user_id = validate_user_id(user_id)
    client = get_client()

    all_goals, metric_target_dates = await asyncio.gather(
        _fetch_all_goals(client, {"goal_owner_id": user_id, "goal_status": 1}),
        _fetch_target_date_map(client),
    )

    return {
        "objectives": [_format_goal(g, metric_target_dates) for g in all_goals],
    }


async def get_objective_details(
    user_id: int,
    objective_id: int,
) -> dict[str, Any]:
    """Get details for a specific objective including key results.

    Args:
        user_id: User ID (positive integer)
        objective_id: Objective ID (positive integer)

    Returns:
        Objective details dictionary with key results
    """
    user_id = validate_user_id(user_id)
    objective_id = validate_objective_id(objective_id)
    client = get_client()

    response, metric_target_dates = await asyncio.gather(
        client.get(f"/user/{user_id}/goal/{objective_id}"),
        _fetch_target_date_map(client),
    )

    goal = response.get("data", {}).get("user", {}).get("goal", {})
    if isinstance(goal, dict) and goal:
        return {"objective": _format_goal(goal, metric_target_dates)}

    return {"objective": response}


async def _get_objective_ids_from_metrics(
    client: Any,
) -> tuple[list[int], dict[int, str]]:
    """Discover objective IDs and build a target-date lookup from the /metric endpoint.

    The /metric endpoint returns all key results the user has access to. Each metric
    contains a goal_id linking it to its parent objective and a real target_date that
    is absent from nested metric objects within goal responses.

    Returns:
        Tuple of:
        - Sorted list of unique objective IDs from current-year metrics
        - Dict mapping metric_id → "YYYY-MM-DD" target date for all fetched metrics
    """
    response = await client.get("/metric")

    metric_body = response.get("data", {})
    all_metrics = metric_body.get("metric", []) if isinstance(metric_body, dict) else []

    target_date_map: dict[int, str] = {}
    for m in all_metrics:
        mid = m.get("metric_id")
        if mid is not None:
            try:
                target_date_map[int(mid)] = _format_date(m.get("target_date"))
            except (ValueError, TypeError):
                continue

    year_start = _current_year_start()
    current_year_metrics = [m for m in all_metrics if int(m.get("target_date") or 0) >= year_start]

    goal_ids: set[int] = set()
    for m in current_year_metrics:
        gid = m.get("metric_goal_id")
        if gid is not None:
            try:
                goal_ids.add(int(gid))
            except (ValueError, TypeError):
                continue

    return sorted(goal_ids), target_date_map


async def _fetch_target_date_map(client: Any) -> dict[int, str]:
    """Fetch the /metric endpoint and return a {metric_id: target_date} lookup.

    Used to enrich nested key results within objectives. Fails gracefully —
    callers receive an empty dict when the fetch fails, which means nested KRs
    will have empty target_date strings rather than raising an error.
    """
    try:
        response = await client.get("/metric")
        metric_body = response.get("data", {})
        metrics = metric_body.get("metric", []) if isinstance(metric_body, dict) else []
        return {
            int(m["metric_id"]): _format_date(m.get("target_date"))
            for m in metrics
            if m.get("metric_id") is not None
        }
    except Exception:
        logger.warning("Could not fetch metric target dates for enrichment")
        return {}


async def get_my_objectives(
    objective_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Get the current user's objectives with key results.

    When objective IDs are provided, fetches each individually (explicit override).
    When no IDs are provided, auto-discovers objectives by fetching all metrics
    and extracting parent goal IDs, then fetching each objective individually.

    Args:
        objective_ids: Optional list of objective IDs to fetch. If not provided,
                       objectives are auto-discovered from the user's key results.

    Returns:
        Dictionary with objectives list
    """
    client = get_client()

    user_response = await client.get("/user")
    try:
        user_id = int(user_response["data"]["user"]["user_id"])
    except (KeyError, TypeError, ValueError):
        return {"error": "Could not determine current user ID"}

    metric_target_dates: dict[int, str] = {}
    if objective_ids is None:
        objective_ids, metric_target_dates = await _get_objective_ids_from_metrics(client)
        if not objective_ids:
            return {
                "objectives": [],
                "message": (
                    "No objectives found. No current-year key results were found "
                    "that link to objectives. You can provide objective IDs explicitly."
                ),
            }
    else:
        metric_target_dates = await _fetch_target_date_map(client)

    objectives: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for oid in objective_ids:
        validated_oid = validate_objective_id(oid)
        try:
            detail = await client.get(f"/user/{user_id}/goal/{validated_oid}")
            goal = detail.get("data", {}).get("user", {}).get("goal", {})
            if isinstance(goal, dict) and goal:
                objectives.append(_format_goal(goal, metric_target_dates))
            else:
                objectives.append(detail)
        except UserError:
            skipped.append(
                {
                    "objective_id": validated_oid,
                    "error": "Not accessible (may be archived or from a prior year)",
                }
            )

    result: dict[str, Any] = {"objectives": objectives}
    if skipped:
        result["skipped"] = skipped
    return result


async def get_my_key_results(
    include_prior_years: bool = False,
) -> dict[str, Any]:
    """List all key results (metrics) the current user owns or has access to.

    By default, only returns key results with a target date in the current
    calendar year or later. Set include_prior_years=True for all key results.

    Args:
        include_prior_years: If True, include key results from prior years.
                             Defaults to False (current year only).

    Returns:
        Dictionary containing list of key results with their IDs, names,
        current values, and targets
    """
    client = get_client()

    response = await client.get("/metric")

    metric_body = response.get("data", {})
    metrics = metric_body.get("metric", []) if isinstance(metric_body, dict) else []

    if not include_prior_years:
        year_start = _current_year_start()
        metrics = [m for m in metrics if int(m.get("target_date") or 0) >= year_start]

    formatted = [_format_metric(m) for m in metrics]

    return {"key_results": formatted}


async def get_user_key_results(
    user_id: int,
    include_prior_years: bool = False,
) -> dict[str, Any]:
    """List key results (metrics) accessible to a specific WorkBoard user.

    Fetches metrics via /user/{user_id}/metric. The response may include
    metrics the user owns or is associated with, depending on WorkBoard
    access rules.

    By default, only returns key results with a target date in the current
    calendar year or later. Set include_prior_years=True for all key results.

    Args:
        user_id: User ID (positive integer)
        include_prior_years: If True, include key results from prior years.
                             Defaults to False (current year only).

    Returns:
        Dictionary containing list of key results with their IDs, names,
        current values, and targets
    """
    user_id = validate_user_id(user_id)
    client = get_client()

    response = await client.get(f"/user/{user_id}/metric")

    metric_body = response.get("data", {})

    if isinstance(metric_body, dict):
        metrics = metric_body.get("metric") or metric_body.get("user", {}).get("metric") or []
    else:
        metrics = []

    if not isinstance(metrics, list):
        metrics = []

    if not include_prior_years:
        year_start = _current_year_start()
        metrics = [m for m in metrics if int(m.get("target_date") or 0) >= year_start]

    formatted = [_format_metric(m) for m in metrics]

    return {"key_results": formatted}


async def update_key_result(
    metric_id: int,
    value: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """Update progress on a key result (metric).

    Includes input validation, read-back-before-write guard to warn on
    significant decreases, and audit logging.

    Args:
        metric_id: Metric ID (positive integer)
        value: The new progress value (e.g. "75")
        comment: Optional check-in comment

    Returns:
        Updated metric details (includes warning if value was decreased)
    """
    metric_id = validate_metric_id(metric_id)

    validated = UpdateKeyResultInput(value=value, comment=comment)

    client = get_client()

    current_value: float | None = None
    metric_name: str = f"metric/{metric_id}"
    try:
        current_response = await client.get("/metric")
        current_metrics = current_response.get("data", {}).get("metric", [])
        for m in current_metrics:
            if int(m.get("metric_id", 0)) == metric_id:
                current_value = float(m.get("metric_achieve_target") or 0)
                metric_name = m.get("metric_name", metric_name)
                break
    except Exception:
        logger.warning("Could not read current value for metric %d", metric_id)

    new_value = float(validated.value)

    warning: str | None = None
    if current_value is not None and new_value < current_value:
        warning = (
            f"Value decreased from {current_value} to {new_value} "
            f"for '{metric_name}' (key_result_id={metric_id})"
        )
        logger.warning("AUDIT: Key result decrease — %s", warning)

    payload: dict[str, str] = {"metric_data": validated.value}
    if validated.comment is not None:
        payload["metric_comment"] = validated.comment

    response = await client.put(f"/metric/{metric_id}", json_data=payload)

    logger.info(
        "AUDIT: Key result updated — metric_id=%d, new_value=%s, comment=%s",
        metric_id,
        validated.value,
        validated.comment or "(none)",
    )

    # Normalize the raw PUT response to OKR vocabulary rather than leaking the
    # API's metric_* fields back to the caller.
    updated = response.get("metric") if isinstance(response, dict) else None
    if updated is None and isinstance(response, dict):
        updated = response.get("data", {}).get("metric")
    if isinstance(updated, list):
        updated = updated[0] if updated else None
    if isinstance(updated, dict) and updated.get("metric_id") is not None:
        formatted_key_result: dict[str, Any] = _format_metric(updated)
    else:
        formatted_key_result = {"key_result_id": metric_id, "value": validated.value}

    result: dict[str, Any] = {"key_result": formatted_key_result}
    if warning:
        result["warning"] = warning
    return result


# Without these cadence/shape fields — metric_source_from above all — the API
# silently drops the metric from a goal-create call instead of erroring (verified
# live). Defaults: individual-sourced, monthly, counting up, scored on last update.
_METRIC_DEFAULTS = {
    "metric_source_from": "1",  # sourced from an individual user
    "metric_update_interval": "3",  # monthly
    "metric_counting_type": "1",  # counting up
    "metric_progress_type": "1",  # last update
}


def _key_result_to_metric(kr: KeyResultInput, owner: str) -> dict[str, str]:
    """Map an OKR-vocabulary key result to the WorkBoard API's ``metric_*`` fields.

    The API creates key results only through the ``goal_metrics`` array on a
    goal-create call, and only when the field names and cadence fields match its
    contract. ``start_value``/``unit_type`` map to ``metric_initial_data``/a numeric
    ``metric_unit``, not the ``metric_start``/``metric_type`` the early code sent.
    """
    metric: dict[str, str] = {
        "metric_name": kr.name,
        "metric_owner": owner,
        "metric_initial_data": kr.start_value or "0",
        "metric_unit": metric_unit_code(kr.unit_type),
        **_METRIC_DEFAULTS,
    }
    if kr.target_value is not None:
        metric["metric_target"] = kr.target_value
    return metric


async def create_objective(
    name: str,
    owner: str,
    start_date: str,
    target_date: str,
    narrative: str | None = None,
    objective_type: str = "team",
    team: str | None = None,
    permission: str | None = None,
    key_results: list[KeyResultInput] | None = None,
) -> dict[str, Any]:
    """Create a new objective with optional key results.

    Creating both Team and Individual objectives works via the API. Objective
    creation requires an OAuth token whose account has the Data-Admin role;
    instant JWT tokens (``isSuperUser: false``) cannot create objectives.
    Note: the API has no update or delete for objectives — edits and deletes
    must be done in the WorkBoard UI.

    Args:
        name: Objective name
        owner: Owner's email address or user ID
        start_date: Start date (YYYY-MM-DD format)
        target_date: Target completion date (YYYY-MM-DD format)
        narrative: Optional description/narrative for the objective
        objective_type: "team" (default) or "individual"
        team: Team ID (or name) — required for team objectives, ignored for individual
        permission: Visibility, comma-separated. Team objectives accept
                    team/report/internal/any; personal objectives accept
                    owner/manager. Defaults by type when omitted (team →
                    "internal,team", individual → "owner").
        key_results: Optional list of key results, each with a name and optional
                     start_value, target_value, and unit_type

    Returns:
        Created objective details
    """
    validated = CreateObjectiveInput(
        name=name,
        owner=owner,
        start_date=start_date,
        target_date=target_date,
        narrative=narrative,
        objective_type=objective_type,
        team=team,
        permission=permission,
    )

    # goal_type "1" is a team objective, which the API requires be tied to a team.
    if validated.objective_type == "1" and validated.team is None:
        raise UserError(
            "A team objective requires a team. Pass team=<team id>, or set "
            "objective_type='individual'. Find team IDs with workboard_get_teams_tool."
        )

    goal: dict[str, Any] = {
        "goal_name": validated.name,
        "goal_owner": validated.owner,
        "goal_start_date": validated.start_date,
        "goal_target_date": validated.target_date,
        "goal_type": validated.objective_type,
        "goal_permission": validated.permission,
    }

    if validated.team is not None:
        goal["goal_team"] = [{"id": validated.team}]

    if validated.narrative is not None:
        goal["goal_narrative"] = validated.narrative

    if key_results:
        goal["goal_metrics"] = [
            _key_result_to_metric(KeyResultInput.model_validate(kr), validated.owner)
            for kr in key_results
        ]

    client = get_client()

    response = await client.post("/goal", json_data={"goals": [goal]})

    logger.info(
        "AUDIT: Objective created — name=%r, owner=%s, dates=%s to %s",
        validated.name,
        validated.owner,
        validated.start_date,
        validated.target_date,
    )

    return {"objective": response}
