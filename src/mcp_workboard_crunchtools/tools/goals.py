"""Goal management tools.

Tools for retrieving WorkBoard goals and goal details.
"""

from typing import Any

from ..client import get_client
from ..models import validate_goal_id, validate_user_id


async def get_goals(
    user_id: int,
) -> dict[str, Any]:
    """Get all goals for a WorkBoard user.

    Args:
        user_id: User ID (positive integer)

    Returns:
        Dictionary containing list of goals
    """
    user_id = validate_user_id(user_id)
    client = get_client()

    response = await client.get(f"/user/{user_id}/goal")

    return {"goals": response}


async def get_goal_details(
    user_id: int,
    goal_id: int,
) -> dict[str, Any]:
    """Get details for a specific goal.

    Args:
        user_id: User ID (positive integer)
        goal_id: Goal ID (positive integer)

    Returns:
        Goal details dictionary
    """
    user_id = validate_user_id(user_id)
    goal_id = validate_goal_id(goal_id)
    client = get_client()

    response = await client.get(f"/user/{user_id}/goal/{goal_id}")

    return {"goal": response}
