"""Action item (activity) management tools.

Tools for listing, retrieving, creating, and updating WorkBoard action items.
Action items are the individual work cards that live inside workstreams.
"""

import logging
from typing import Any

from ..client import get_client
from ..models import (
    CreateActivityInput,
    UpdateActivityInput,
    validate_activity_id,
)

logger = logging.getLogger(__name__)


def _format_activity(ai: dict[str, Any]) -> dict[str, Any]:
    """Format a raw action item from an API response."""
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
        "workstream": ai.get("ai_workstream", ""),
        "workstream_name": ai.get("ai_workstream_name", ""),
        "team": ai.get("ai_team", ""),
    }

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


async def list_activities(
    ai_owner: str | None = None,
    ai_state: str | None = None,
    ai_priority: str | None = None,
    ai_effort: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """List action items accessible to the authenticated user.

    Args:
        ai_owner: Filter by owner user ID or email.
        ai_state: Filter by state (next, doing, done, pause).
        ai_priority: Filter by priority (low, med, high).
        ai_effort: Filter by effort (easy, medium, huge).
        limit: Maximum number of results (default 15 per API).
        offset: Pagination offset.

    Returns:
        Dictionary with activities list.
    """
    client = get_client()

    params: dict[str, Any] = {}
    if ai_owner is not None:
        params["ai_owner"] = ai_owner
    if ai_state is not None:
        params["ai_state"] = ai_state
    if ai_priority is not None:
        params["priority"] = ai_priority
    if ai_effort is not None:
        params["effort"] = ai_effort
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    response = await client.get("/activity", params=params if params else None)
    body = response.get("data", {})

    raw = body.get("activity", [])
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        raw = []

    activities = [_format_activity(ai) for ai in raw if isinstance(ai, dict)]

    result: dict[str, Any] = {"activities": activities}
    count = body.get("activity_count") or body.get("totalCount")
    if count is not None:
        result["total_count"] = count

    return result


async def get_activity(
    activity_id: int,
) -> dict[str, Any]:
    """Get a single action item by ID.

    Args:
        activity_id: Action item ID (positive integer).

    Returns:
        Action item details.
    """
    activity_id = validate_activity_id(activity_id)
    client = get_client()

    response = await client.get(f"/activity/{activity_id}")
    body = response.get("data", {})

    raw = body.get("activity", body)
    if isinstance(raw, dict):
        return {"activity": _format_activity(raw)}

    return {"activity": body}


async def create_activity(
    ai_description: str,
    ai_workstream: str | None = None,
    ai_team: str | None = None,
    ai_owner: str | None = None,
    ai_state: str | None = None,
    ai_priority: str | None = None,
    ai_effort: str | None = None,
    ai_due_date: str | None = None,
) -> dict[str, Any]:
    """Create a new action item.

    Args:
        ai_description: Description of the action item (required).
        ai_workstream: Workstream ID to associate the action item with.
        ai_team: Team ID to associate the action item with.
        ai_owner: Owner user ID or email.
        ai_state: Initial state: next, doing, done, or pause.
        ai_priority: Priority: low, med, or high.
        ai_effort: Effort estimate: easy, medium, or huge.
        ai_due_date: Due date as UNIX timestamp string.

    Returns:
        Created action item details.
    """
    validated = CreateActivityInput(
        ai_description=ai_description,
        ai_workstream=ai_workstream,
        ai_team=ai_team,
        ai_owner=ai_owner,
        ai_state=ai_state,
        ai_priority=ai_priority,
        ai_effort=ai_effort,
        ai_due_date=ai_due_date,
    )

    payload: dict[str, Any] = {"ai_description": validated.ai_description}
    if validated.ai_workstream is not None:
        payload["ai_workstream"] = validated.ai_workstream
    if validated.ai_team is not None:
        payload["ai_team"] = validated.ai_team
    if validated.ai_owner is not None:
        payload["ai_owner"] = validated.ai_owner
    if validated.ai_state is not None:
        payload["ai_state"] = validated.ai_state
    if validated.ai_priority is not None:
        payload["ai_priority"] = validated.ai_priority
    if validated.ai_effort is not None:
        payload["ai_effort"] = validated.ai_effort
    if validated.ai_due_date is not None:
        payload["ai_due_date"] = validated.ai_due_date

    client = get_client()
    response = await client.post("/activity", json_data=payload)

    logger.info(
        "AUDIT: Activity created — description=%r, workstream=%s, owner=%s",
        validated.ai_description,
        validated.ai_workstream,
        validated.ai_owner,
    )

    return {"activity": response}


async def update_activity(
    activity_id: int,
    ai_description: str | None = None,
    ai_owner: str | None = None,
    ai_state: str | None = None,
    ai_priority: str | None = None,
    ai_effort: str | None = None,
    ai_due_date: str | None = None,
) -> dict[str, Any]:
    """Update an existing action item.

    Performs read-before-write to confirm the action item exists, then
    applies the update.

    Args:
        activity_id: Action item ID (positive integer).
        ai_description: New description (optional).
        ai_owner: New owner user ID or email (optional).
        ai_state: New state: next, doing, done, or pause (optional).
        ai_priority: New priority: low, med, or high (optional).
        ai_effort: New effort: easy, medium, or huge (optional).
        ai_due_date: New due date as UNIX timestamp string (optional).

    Returns:
        Updated action item details.
    """
    activity_id = validate_activity_id(activity_id)

    validated = UpdateActivityInput(
        ai_description=ai_description,
        ai_owner=ai_owner,
        ai_state=ai_state,
        ai_priority=ai_priority,
        ai_effort=ai_effort,
        ai_due_date=ai_due_date,
    )

    client = get_client()

    await client.get(f"/activity/{activity_id}")

    payload: dict[str, Any] = {}
    if validated.ai_description is not None:
        payload["ai_description"] = validated.ai_description
    if validated.ai_owner is not None:
        payload["ai_owner"] = validated.ai_owner
    if validated.ai_state is not None:
        payload["ai_state"] = validated.ai_state
    if validated.ai_priority is not None:
        payload["ai_priority"] = validated.ai_priority
    if validated.ai_effort is not None:
        payload["ai_effort"] = validated.ai_effort
    if validated.ai_due_date is not None:
        payload["ai_due_date"] = validated.ai_due_date

    response = await client.put(f"/activity/{activity_id}", json_data=payload)

    logger.info(
        "AUDIT: Activity updated — activity_id=%d, fields=%s",
        activity_id,
        list(payload.keys()),
    )

    return {"activity": response}
