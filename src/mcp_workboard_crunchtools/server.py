"""FastMCP server setup for WorkBoard MCP.

This module creates and configures the MCP server with all tools.
"""

import logging
from typing import Any

from fastmcp import FastMCP

from .tools import (
    create_user,
    get_goal_details,
    get_goals,
    get_user,
    list_users,
    update_user,
)

logger = logging.getLogger(__name__)

# Create the FastMCP server
mcp = FastMCP(
    name="mcp-workboard-crunchtools",
    version="0.1.0",
    instructions="Secure MCP server for WorkBoard OKR and strategy execution platform",
)


# Register User tools


@mcp.tool()
async def workboard_get_user_tool(
    user_id: int | None = None,
) -> dict[str, Any]:
    """Get a WorkBoard user by ID, or the current authenticated user.

    Args:
        user_id: User ID (positive integer). If not provided, returns the
                 current authenticated user.

    Returns:
        User details
    """
    return await get_user(user_id=user_id)


@mcp.tool()
async def workboard_list_users_tool() -> dict[str, Any]:
    """List all WorkBoard users (requires Data-Admin role).

    Returns:
        List of all users
    """
    return await list_users()


@mcp.tool()
async def workboard_create_user_tool(
    first_name: str,
    last_name: str,
    email: str,
    designation: str | None = None,
) -> dict[str, Any]:
    """Create a new WorkBoard user (requires Data-Admin role).

    Args:
        first_name: User's first name
        last_name: User's last name
        email: User's email address
        designation: User's job title or designation

    Returns:
        Created user details
    """
    return await create_user(
        first_name=first_name,
        last_name=last_name,
        email=email,
        designation=designation,
    )


@mcp.tool()
async def workboard_update_user_tool(
    user_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    designation: str | None = None,
) -> dict[str, Any]:
    """Update an existing WorkBoard user.

    Args:
        user_id: User ID (positive integer)
        first_name: User's first name (optional)
        last_name: User's last name (optional)
        email: User's email address (optional)
        designation: User's job title or designation (optional)

    Returns:
        Updated user details
    """
    return await update_user(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        designation=designation,
    )


# Register Goal tools


@mcp.tool()
async def workboard_get_goals_tool(
    user_id: int,
) -> dict[str, Any]:
    """Get all goals for a WorkBoard user.

    Args:
        user_id: User ID (positive integer)

    Returns:
        List of goals for the user
    """
    return await get_goals(user_id=user_id)


@mcp.tool()
async def workboard_get_goal_details_tool(
    user_id: int,
    goal_id: int,
) -> dict[str, Any]:
    """Get details for a specific WorkBoard goal.

    Args:
        user_id: User ID (positive integer)
        goal_id: Goal ID (positive integer)

    Returns:
        Goal details
    """
    return await get_goal_details(user_id=user_id, goal_id=goal_id)
