"""Objective management tools.

Tools for retrieving WorkBoard objectives (goals) and their key results.
WorkBoard uses "goal" in its API, but these tools expose OKR terminology.
"""

from typing import Any

from ..client import get_client
from ..models import validate_objective_id, validate_user_id


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

    return {"objectives": response}


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
    user_response = await client.get("/user")
    user_id: int = user_response.get("user_id", 0)
    if not user_id:
        return {"error": "Could not determine current user ID"}

    if objective_ids is not None:
        # Primary path: fetch each objective by ID
        objectives: list[dict[str, Any]] = []
        for oid in objective_ids:
            validated_oid = validate_objective_id(oid)
            detail = await client.get(f"/user/{user_id}/goal/{validated_oid}")
            objectives.append(detail)

        return {"objectives": objectives, "user_id": user_id}

    # Fallback: list endpoint (capped at 15, returns associated not owned)
    response = await client.get(f"/user/{user_id}/goal")

    # Filter to only objectives owned by this user
    all_goals: list[dict[str, Any]] = response.get("data", [])
    goal_count: int = response.get("goal_count", 0)
    owned = [g for g in all_goals if g.get("goal_owner") == user_id]

    result: dict[str, Any] = {"objectives": owned, "user_id": user_id}

    if goal_count > len(all_goals):
        result["warning"] = (
            f"WorkBoard returned {len(all_goals)} of {goal_count} associated objectives "
            f"(API hard cap). Some owned objectives may be missing. "
            f"For reliable results, provide specific objective IDs."
        )

    return result
