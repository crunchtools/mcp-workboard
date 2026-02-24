"""Objective management tools.

Tools for retrieving and managing WorkBoard objectives (goals) and their key results.
WorkBoard uses "goal" in its API, but these tools expose OKR terminology.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from ..client import get_client
from ..errors import UserError
from ..models import validate_metric_id, validate_objective_id, validate_user_id

logger = logging.getLogger(__name__)


# --- Formatting helpers ---


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


def _format_metric(metric: dict[str, Any]) -> dict[str, Any]:
    """Format a key result metric for human-readable output."""
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

    if unit_name == "Currency":
        progress_str = f"${int(achieved):,} of ${int(target):,}"
    elif unit_name == "Number":
        progress_str = f"{int(achieved)} of {int(target)}"
    else:
        progress_str = f"{int(achieved)}% of {int(target)}%"

    return {
        "metric_id": int(metric.get("metric_id", 0)),
        "name": metric.get("metric_name", ""),
        "progress": progress_str,
    }


def _format_goal(goal: dict[str, Any]) -> dict[str, Any]:
    """Format an objective for human-readable output."""
    try:
        progress = int(float(goal.get("goal_progress") or 0))
    except (ValueError, TypeError):
        progress = 0

    result: dict[str, Any] = {
        "name": goal.get("goal_name", ""),
        "progress": f"{progress}%",
    }

    owner = goal.get("goal_owner_full_name")
    if owner:
        result["owner"] = owner

    team = goal.get("goal_team_name")
    if team:
        result["team"] = team

    start = _format_date(goal.get("goal_start_date"))
    target = _format_date(goal.get("goal_target_date"))
    if start and target:
        result["dates"] = f"{start} to {target}"

    metrics = goal.get("goal_metrics", [])
    if metrics:
        result["key_results"] = [_format_metric(m) for m in metrics]

    return result


def _extract_goals_from_response(response: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    """Extract goals list from the WorkBoard API response.

    The API returns goals as a dict with numeric string keys under
    data.user.goal, e.g. {"0": {goal}, "1": {goal}, "goals_count": 15}.
    This helper normalizes that into a list.

    Returns:
        Tuple of (goals list, total goal count)
    """
    data = response.get("data", {})
    if not isinstance(data, dict):
        return [], 0

    goal_count: int = data.get("goal_count", 0)
    user_data = data.get("user", {})
    if not isinstance(user_data, dict):
        return [], goal_count

    goals_obj = user_data.get("goal", {})

    if isinstance(goals_obj, dict):
        # API returns {"0": {goal}, "1": {goal}, ..., "goals_count": N}
        goals = [
            v for k, v in goals_obj.items()
            if k.isdigit() and isinstance(v, dict)
        ]
    elif isinstance(goals_obj, list):
        goals = goals_obj
    else:
        goals = []

    return goals, goal_count


def _current_year_start() -> int:
    """Get Unix timestamp for Jan 1 of the current year."""
    now = datetime.now(timezone.utc)
    return int(datetime(now.year, 1, 1, tzinfo=timezone.utc).timestamp())


# --- Tool functions ---


async def get_objectives(
    user_id: int,
) -> dict[str, Any]:
    """Get objectives associated with a WorkBoard user.

    Note: The WorkBoard API caps this endpoint at 15 results and returns
    objectives the user is associated with, not necessarily ones they own.
    For owned objectives, use get_my_objectives() with specific IDs.

    Args:
        user_id: User ID (positive integer)

    Returns:
        Dictionary containing list of objectives
    """
    user_id = validate_user_id(user_id)
    client = get_client()

    response = await client.get(f"/user/{user_id}/goal")

    goals, goal_count = _extract_goals_from_response(response)
    result: dict[str, Any] = {"objectives": [_format_goal(g) for g in goals]}
    if goal_count > len(goals):
        result["warning"] = (
            f"Showing {len(goals)} of {goal_count} objectives (API cap). "
            f"Some objectives may be missing."
        )
    return result


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

    response = await client.get(f"/user/{user_id}/goal/{objective_id}")

    # Detail endpoint: data.user.goal is a single goal dict
    goal = response.get("data", {}).get("user", {}).get("goal", {})
    if isinstance(goal, dict) and goal:
        return {"objective": _format_goal(goal)}

    return {"objective": response}


async def get_my_objectives(
    objective_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Get the current user's owned objectives with key results.

    When objective IDs are provided, fetches each individually via the
    detail endpoint (reliable). When no IDs are provided, falls back to
    the list endpoint which is capped at 15 results and filters by ownership.

    Args:
        objective_ids: Optional list of objective IDs to fetch individually.
                       This is the recommended approach since the list endpoint
                       has a hard cap of 15 results.

    Returns:
        Dictionary with objectives list and optional warning about truncation
    """
    client = get_client()

    # Get current user's ID
    # API returns: {"data": {"user": {"user_id": "123", ...}}}
    user_response = await client.get("/user")
    try:
        user_id = int(user_response["data"]["user"]["user_id"])
    except (KeyError, TypeError, ValueError):
        return {"error": "Could not determine current user ID"}

    if objective_ids is not None:
        # Primary path: fetch each objective by ID (handles archived gracefully)
        objectives: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for oid in objective_ids:
            validated_oid = validate_objective_id(oid)
            try:
                detail = await client.get(f"/user/{user_id}/goal/{validated_oid}")
                goal = detail.get("data", {}).get("user", {}).get("goal", {})
                if isinstance(goal, dict) and goal:
                    objectives.append(_format_goal(goal))
                else:
                    objectives.append(detail)
            except UserError:
                skipped.append({
                    "objective_id": validated_oid,
                    "error": "Not accessible (may be archived or from a prior year)",
                })

        result: dict[str, Any] = {"objectives": objectives}
        if skipped:
            result["skipped"] = skipped
        return result

    # Fallback: list endpoint (capped at 15, returns associated not owned)
    response = await client.get(f"/user/{user_id}/goal")

    all_goals, goal_count = _extract_goals_from_response(response)

    # Filter to only objectives owned by this user
    uid_str = str(user_id)
    owned = [
        g for g in all_goals
        if isinstance(g, dict) and str(g.get("goal_owner", "")) == uid_str
    ]

    formatted = [_format_goal(g) for g in owned]
    result = {"objectives": formatted}

    if goal_count > len(all_goals):
        result["warning"] = (
            f"WorkBoard returned {len(all_goals)} of {goal_count} associated objectives "
            f"(API hard cap). Some owned objectives may be missing. "
            f"For reliable results, provide specific objective IDs."
        )

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

    data = response.get("data", {})
    metrics = data.get("metric", []) if isinstance(data, dict) else []

    if not include_prior_years:
        year_start = _current_year_start()
        metrics = [
            m for m in metrics
            if int(m.get("target_date") or 0) >= year_start
        ]

    formatted = []
    for m in metrics:
        entry = _format_metric(m)
        entry["target_date"] = _format_date(m.get("target_date"))
        formatted.append(entry)

    return {"key_results": formatted}


async def update_key_result(
    metric_id: int,
    value: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """Update progress on a key result (metric).

    Args:
        metric_id: Metric ID (positive integer)
        value: The new progress value (e.g. "75")
        comment: Optional check-in comment

    Returns:
        Updated metric details
    """
    metric_id = validate_metric_id(metric_id)

    payload: dict[str, str] = {"metric_data": value}
    if comment is not None:
        payload["metric_comment"] = comment

    client = get_client()

    response = await client.put(f"/metric/{metric_id}", json_data=payload)

    return {"key_result": response}


async def create_objective(
    name: str,
    owner: str,
    start_date: str,
    target_date: str,
    narrative: str | None = None,
    goal_type: str = "1",
    permission: str = "internal,team",
    key_results: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Create a new objective with optional key results (requires Data-Admin token).

    Args:
        name: Objective name
        owner: Owner's email address or user ID
        start_date: Start date (YYYY-MM-DD format)
        target_date: Target completion date (YYYY-MM-DD format)
        narrative: Optional description/narrative for the objective
        goal_type: "1" for Team objective, "2" for Personal objective
        permission: Visibility setting (default "internal,team")
        key_results: Optional list of key result dicts, each with keys like
                     "metric_name", "metric_start", "metric_target", "metric_type"

    Returns:
        Created objective details
    """
    goal: dict[str, Any] = {
        "goal_name": name,
        "goal_owner": owner,
        "goal_start_date": start_date,
        "goal_target_date": target_date,
        "goal_type": goal_type,
        "goal_permission": permission,
    }

    if narrative is not None:
        goal["goal_narrative"] = narrative

    if key_results is not None:
        goal["metrics"] = key_results

    client = get_client()

    response = await client.post("/goal", json_data={"goals": [goal]})

    return {"objective": response}
