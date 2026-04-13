"""Workstream management tools.

Tools for retrieving and managing WorkBoard workstreams and their action items.
Workstreams are team-level work containers that track activities, action items,
pace, health, and priority.
"""

import logging
from typing import Any

from ..client import get_client
from ..models import (
    CreateWorkstreamInput,
    UpdateWorkstreamInput,
    validate_workstream_id,
)

logger = logging.getLogger(__name__)


def _format_activity_item(ai: dict[str, Any]) -> dict[str, Any]:
    """Format a raw action item from a workstream activity response."""
    formatted: dict[str, Any] = {
        "ai_id": ai.get("ai_id", ""),
        "description": ai.get("ai_description", ""),
        "state": ai.get("ai_state", ""),
        "priority": ai.get("ai_priority", ""),
        "effort": ai.get("ai_effort", ""),
        "due_date": ai.get("ai_due_date", ""),
        "owner": ai.get("ai_owner", ""),
        "created_by": ai.get("ai_created_by", ""),
        "created_at": ai.get("ai_created_at", ""),
        "completed_at": ai.get("ai_completed_at"),
        "url": ai.get("ai_url", ""),
    }

    ai_column = ai.get("ai_column")
    if isinstance(ai_column, dict):
        formatted["column_id"] = ai_column.get("id", "")
        formatted["column_name"] = ai_column.get("name", "")

    comments = ai.get("ai_comments", [])
    if isinstance(comments, list) and comments:
        formatted["comments"] = [
            {
                "comment_id": c.get("comment_id", ""),
                "comment": c.get("comment", ""),
                "owner": c.get("comment_owner", ""),
                "timestamp": c.get("comment_timestamp", ""),
            }
            for c in comments
            if isinstance(c, dict)
        ]

    sub_actions = ai.get("ai_sub_actions", [])
    if isinstance(sub_actions, list) and sub_actions:
        formatted["sub_actions"] = [
            {
                "sub_ai_id": sa.get("sub_ai_id", ""),
                "description": sa.get("sub_ai_description", ""),
                "owner": sa.get("sub_ai_owner", ""),
            }
            for sa in sub_actions
            if isinstance(sa, dict)
        ]

    files = ai.get("ai_files", [])
    if isinstance(files, list) and files:
        formatted["files"] = [
            {
                "file_id": f.get("file_id", ""),
                "file_name": f.get("file_name", ""),
                "file_url": f.get("file_url", ""),
                "file_owner": f.get("file_owner", ""),
            }
            for f in files
            if isinstance(f, dict)
        ]

    tags = ai.get("ai_tags")
    if tags:
        formatted["tags"] = tags

    loop_members = ai.get("ai_loop_members", [])
    if isinstance(loop_members, list) and loop_members:
        formatted["loop_members"] = [
            {
                "user_id": lm.get("user_id", ""),
                "email": lm.get("user_email", ""),
            }
            for lm in loop_members
            if isinstance(lm, dict)
        ]

    return formatted


def _format_workstream(ws: dict[str, Any]) -> dict[str, Any]:
    """Format a raw workstream object for MCP output."""
    formatted: dict[str, Any] = {
        "ws_id": ws.get("ws_id", ""),
        "name": ws.get("ws_name", ""),
        "objective": ws.get("ws_objective", ""),
        "owner": ws.get("ws_owner", ""),
        "lead": ws.get("ws_lead", ""),
        "status": ws.get("ws_status", ""),
        "type": ws.get("ws_type", ""),
        "pace": ws.get("ws_pace", ""),
        "health": ws.get("ws_health", ""),
        "priority": ws.get("ws_priority", ""),
        "progress": ws.get("ws_progress"),
        "start_date": ws.get("ws_start_date", ""),
        "target_date": ws.get("ws_target_date"),
        "completion_date": ws.get("ws_completion_date"),
        "team_id": ws.get("ws_team_id", ""),
        "team_name": ws.get("ws_team_name", ""),
    }

    effort = ws.get("ws_effort")
    if isinstance(effort, dict):
        formatted["effort"] = {
            "low": effort.get("low_effort", ""),
            "medium": effort.get("medium_effort", ""),
            "large": effort.get("large_effort", ""),
        }

    activity_data = ws.get("ws_activity")
    if isinstance(activity_data, dict):
        activities = activity_data.get("activity", [])
        if isinstance(activities, list) and activities:
            formatted["action_items"] = [
                _format_activity_item(ai) for ai in activities if isinstance(ai, dict)
            ]
            count = activity_data.get("activity_count")
            if count is not None:
                formatted["action_item_count"] = count

    return formatted


def _extract_workstreams(response_body: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract workstream list from API response body.

    The /workstream endpoint returns either a single object (when ws_id is
    passed) or an array. This helper normalizes both forms into a list.
    """
    raw = response_body.get("workstream", [])
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [ws for ws in raw if isinstance(ws, dict)]
    return []


async def get_workstreams(
    ws_id: int | None = None,
) -> dict[str, Any]:
    """Get team workstreams accessible to the authenticated user.

    When ws_id is provided, returns a single workstream. Otherwise returns
    all team workstreams the user has access to.

    Args:
        ws_id: Optional workstream ID to fetch a specific workstream.

    Returns:
        Dictionary with workstreams list.
    """
    if ws_id is not None:
        ws_id = validate_workstream_id(ws_id)

    client = get_client()

    params: dict[str, Any] = {}
    if ws_id is not None:
        params["ws_id"] = ws_id

    response = await client.get("/workstream", params=params if params else None)
    ws_body = response.get("data", {})
    workstreams = _extract_workstreams(ws_body)

    return {"workstreams": [_format_workstream(ws) for ws in workstreams]}


async def get_workstream_activities(
    ws_id: int,
) -> dict[str, Any]:
    """Get a workstream's full details including all action items.

    Args:
        ws_id: Workstream ID (positive integer).

    Returns:
        Workstream details with action items.
    """
    ws_id = validate_workstream_id(ws_id)
    client = get_client()

    response = await client.get(f"/workstream/{ws_id}/activity")
    activity_body = response.get("data", {})

    ws_data = activity_body.get("workstream", {})
    if isinstance(ws_data, dict) and ws_data:
        return {"workstream": _format_workstream(ws_data)}

    return {"workstream": activity_body}


async def get_team_workstreams(
    team_id: int,
) -> dict[str, Any]:
    """Get all workstreams belonging to a specific team.

    Args:
        team_id: Team ID (positive integer).

    Returns:
        Dictionary with team info and workstreams list.
    """
    from ..models import validate_user_id as _validate_team_id

    team_id = _validate_team_id(team_id)
    client = get_client()

    response = await client.get(f"/team/{team_id}/workstream")
    team_body = response.get("data", {})

    team_data = team_body.get("team", {})
    if not isinstance(team_data, dict):
        team_data = {}

    ws_section = team_data.get("team_workstream", {})
    if not isinstance(ws_section, dict):
        ws_section = {}

    raw_ws = ws_section.get("workstream", [])
    if not isinstance(raw_ws, list):
        raw_ws = []

    return {
        "team_id": team_id,
        "team_name": team_data.get("team_name", ""),
        "workstream_count": ws_section.get("workstream_count", "0"),
        "workstreams": [_format_workstream(ws) for ws in raw_ws if isinstance(ws, dict)],
    }


async def create_workstream(
    ws_name: str,
    team_id: str,
    ws_owner: str,
    ws_objective: str | None = None,
) -> dict[str, Any]:
    """Create a new workstream for a team.

    Requires team manager or co-manager permissions.

    Args:
        ws_name: Name of the workstream.
        team_id: Parent team ID.
        ws_owner: User ID of the team manager or co-manager.
        ws_objective: Optional descriptive narrative.

    Returns:
        Created workstream details.
    """
    validated = CreateWorkstreamInput(
        ws_name=ws_name,
        team_id=team_id,
        ws_owner=ws_owner,
        ws_objective=ws_objective,
    )

    ws_item: dict[str, str] = {
        "ws_name": validated.ws_name,
        "team_id": validated.team_id,
        "ws_owner": validated.ws_owner,
    }
    if validated.ws_objective is not None:
        ws_item["ws_objective"] = validated.ws_objective

    client = get_client()
    response = await client.post("/workstream", json_data={"ws_data": [ws_item]})

    logger.info(
        "AUDIT: Workstream created — name=%r, team_id=%s, owner=%s",
        validated.ws_name,
        validated.team_id,
        validated.ws_owner,
    )

    return {"workstream": response}


async def update_workstream(
    ws_id: int,
    ws_name: str | None = None,
    ws_start_date: str | None = None,
    ws_end_date: str | None = None,
    ws_pace: str | None = None,
    ws_health: str | None = None,
    ws_priority: str | None = None,
) -> dict[str, Any]:
    """Update an existing workstream.

    Performs read-before-write to confirm the workstream exists, then applies
    the update. Requires team manager or co-manager permissions.

    Args:
        ws_id: Workstream ID (positive integer).
        ws_name: New name (optional).
        ws_start_date: Start date in YYYY-MM-DD (optional).
        ws_end_date: End date in YYYY-MM-DD (optional).
        ws_pace: Pace: slow, fast, or steady (optional).
        ws_health: Health: ok, good, or risk (optional).
        ws_priority: Priority: p1 through p5 (optional).

    Returns:
        Updated workstream details.
    """
    ws_id = validate_workstream_id(ws_id)

    validated = UpdateWorkstreamInput(
        ws_name=ws_name,
        ws_start_date=ws_start_date,
        ws_end_date=ws_end_date,
        ws_pace=ws_pace,
        ws_health=ws_health,
        ws_priority=ws_priority,
    )

    client = get_client()

    await client.get("/workstream", params={"ws_id": ws_id})

    payload: dict[str, Any] = {}
    if validated.ws_name is not None:
        payload["ws_name"] = validated.ws_name
    if validated.ws_start_date is not None:
        payload["ws_start_date"] = validated.ws_start_date
    if validated.ws_end_date is not None:
        payload["ws_end_date"] = validated.ws_end_date
    if validated.ws_pace is not None:
        payload["ws_pace"] = validated.ws_pace
    if validated.ws_health is not None:
        payload["ws_health"] = validated.ws_health
    if validated.ws_priority is not None:
        payload["ws_priority"] = validated.ws_priority

    response = await client.put(f"/workstream/{ws_id}", json_data=payload)

    logger.info(
        "AUDIT: Workstream updated — ws_id=%d, fields=%s",
        ws_id,
        list(payload.keys()),
    )

    return {"workstream": response}
