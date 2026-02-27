"""FastMCP server setup for WorkBoard MCP.

This module creates and configures the MCP server with all tools.
"""

import logging
from typing import Any

from fastmcp import FastMCP

from .tools import (
    create_objective,
    create_user,
    get_my_key_results,
    get_my_objectives,
    get_objective_details,
    get_objectives,
    get_team_members,
    get_teams,
    get_user,
    get_user_key_results,
    list_users,
    update_key_result,
    update_user,
)

logger = logging.getLogger(__name__)

# Create the FastMCP server
mcp = FastMCP(
    name="mcp-workboard-crunchtools",
    version="0.4.0",
    instructions=(
        "Secure MCP server for WorkBoard OKR and strategy execution platform. "
        "WorkBoard tracks Objectives (goals) and Key Results (metrics). "
        "When users ask about 'my objectives' or 'my OKRs', use workboard_get_my_objectives_tool "
        "with no arguments — it auto-discovers objectives from the user's key results. "
        "To update OKR progress, first use workboard_get_my_key_results_tool to find metric IDs, "
        "then use workboard_update_key_result_tool to check in. "
        "To identify the current user, call workboard_get_user_tool with no arguments. "
        "\n\n"
        "DISPLAY FORMAT: When showing objectives and key results, always use a tree structure. "
        "Show each objective as a top-level item with its progress, then indent its key results "
        "beneath it. Example:\n"
        "- Objective Name (progress%)\n"
        "  - Key Result 1: current of target\n"
        "  - Key Result 2: current of target\n"
        "For key result lists without objectives, use a flat bulleted list with name, progress, "
        "and target date."
    ),
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


# Register Team tools


@mcp.tool()
async def workboard_get_teams_tool() -> dict[str, Any]:
    """Get all teams the authenticated user belongs to.

    Returns team IDs, names, and owner user IDs. Use workboard_get_team_members_tool
    to get the full member list (with user_ids) for a specific team.

    Returns:
        List of teams with team_id, team_name, team_owner_id, is_team_owner
    """
    return await get_teams()


@mcp.tool()
async def workboard_get_team_members_tool(team_id: int) -> dict[str, Any]:
    """Get all members of a WorkBoard team, including their user IDs and emails.

    Use this to resolve a person's name or email to their WorkBoard user_id.
    Combine with workboard_get_objectives_tool(user_id) to fetch their OKRs.

    Args:
        team_id: The WorkBoard team ID (get from workboard_get_teams_tool)

    Returns:
        team_id, team_name, and members list with user_id, full_name, email, team_role
    """
    return await get_team_members(team_id=team_id)


# Register Objective tools


@mcp.tool()
async def workboard_get_objectives_tool(
    user_id: int,
) -> dict[str, Any]:
    """Get objectives associated with a WorkBoard user by their user ID.

    WARNING: This endpoint has a hard cap of 15 results and returns objectives
    the user is *associated with* (contributor, viewer, etc.), NOT necessarily
    ones they own. Prefer workboard_get_my_objectives_tool when the user wants
    to see their own objectives.

    Use workboard_get_user_tool (no arguments) to find the current user's ID.

    Args:
        user_id: User ID (positive integer). Get this from workboard_get_user_tool.

    Returns:
        List of up to 15 associated objectives (may be incomplete)
    """
    return await get_objectives(user_id=user_id)


@mcp.tool()
async def workboard_get_objective_details_tool(
    user_id: int,
    objective_id: int,
) -> dict[str, Any]:
    """Get full details for a single objective including all its key results.

    Returns the objective name, progress, status, dates, and all key results
    (metrics) with their targets, progress, and update schedules.

    Use workboard_get_user_tool (no arguments) to find the current user's ID.

    Args:
        user_id: User ID (positive integer). Get this from workboard_get_user_tool.
        objective_id: Objective ID (positive integer).

    Returns:
        Full objective details with key results (metrics)
    """
    return await get_objective_details(user_id=user_id, objective_id=objective_id)


@mcp.tool()
async def workboard_get_my_objectives_tool(
    objective_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Get the current authenticated user's objectives with key results.

    This is the RECOMMENDED tool when users ask about "my objectives" or "my OKRs".
    It automatically determines the current user and discovers their objectives
    from their key results — no IDs needed.

    Args:
        objective_ids: Optional list of specific objective IDs to fetch.
                       If not provided, objectives are auto-discovered from
                       the user's key results.

    Returns:
        List of objectives with their key results (metrics)
    """
    return await get_my_objectives(objective_ids=objective_ids)


# Register Key Result tools


@mcp.tool()
async def workboard_get_my_key_results_tool(
    include_prior_years: bool = False,
) -> dict[str, Any]:
    """List all key results (metrics) the current user owns or has access to.

    Use this to find metric IDs and see current progress before updating
    with workboard_update_key_result_tool. Returns metric names, current
    values, targets, and IDs.

    By default, only shows current year key results. Set include_prior_years=True
    to see key results from previous years.

    Args:
        include_prior_years: If True, include key results from prior years.
                             Defaults to False (current year only).

    Returns:
        List of key results with IDs, names, values, and targets
    """
    return await get_my_key_results(include_prior_years=include_prior_years)


@mcp.tool()
async def workboard_get_user_key_results_tool(
    user_id: int,
    include_prior_years: bool = False,
) -> dict[str, Any]:
    """List key results (metrics) for a specific WorkBoard user by their user ID.

    Use this to see KRs owned by or associated with any user — for example,
    to review a direct report's key results before a 1:1. Skills layer maps
    organizational roles (e.g. "direct report") to user IDs; this tool only
    knows about WorkBoard user IDs.

    Use workboard_get_teams_tool and workboard_get_team_members_tool to
    resolve a person's name to their user ID.

    By default, only shows current year key results. Set include_prior_years=True
    to see key results from previous years.

    Args:
        user_id: User ID (positive integer). Get this from workboard_get_team_members_tool.
        include_prior_years: If True, include key results from prior years.
                             Defaults to False (current year only).

    Returns:
        List of key results with IDs, names, values, and targets
    """
    return await get_user_key_results(user_id=user_id, include_prior_years=include_prior_years)


@mcp.tool()
async def workboard_update_key_result_tool(
    metric_id: int,
    value: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """Update progress on a key result (metric). This is the primary tool
    for weekly OKR check-ins — update a key result's value without logging
    into WorkBoard.

    Use workboard_get_my_key_results_tool to find metric IDs first.

    Args:
        metric_id: Metric ID (positive integer). Get this from
                   workboard_get_my_key_results_tool.
        value: The new progress value (e.g. "75" for 75%).
        comment: Optional check-in comment describing what changed.

    Returns:
        Updated key result details
    """
    return await update_key_result(
        metric_id=metric_id,
        value=value,
        comment=comment,
    )


@mcp.tool()
async def workboard_create_objective_tool(
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

    Provide the goal name, owner, dates, and optionally key results with targets.
    Each key result dict can include: metric_name, metric_start, metric_target,
    metric_type.

    Args:
        name: Objective name (e.g. "Increase customer retention")
        owner: Owner's email address or user ID
        start_date: Start date in YYYY-MM-DD format
        target_date: Target completion date in YYYY-MM-DD format
        narrative: Optional description/narrative for the objective
        goal_type: "1" for Team objective (default), "2" for Personal objective
        permission: Visibility setting (default "internal,team")
        key_results: Optional list of key result dicts, each with keys like
                     "metric_name", "metric_start", "metric_target", "metric_type"

    Returns:
        Created objective details
    """
    return await create_objective(
        name=name,
        owner=owner,
        start_date=start_date,
        target_date=target_date,
        narrative=narrative,
        goal_type=goal_type,
        permission=permission,
        key_results=key_results,
    )
