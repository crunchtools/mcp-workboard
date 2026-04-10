"""FastMCP server setup for WorkBoard MCP."""

import logging
from typing import Any

from fastmcp import FastMCP

from .tools import (
    create_activity,
    create_objective,
    create_user,
    create_workstream,
    get_activity,
    get_my_key_results,
    get_my_objectives,
    get_objective_details,
    get_objectives,
    get_team_members,
    get_team_workstreams,
    get_teams,
    get_user,
    get_user_key_results,
    get_workstream_activities,
    get_workstreams,
    list_activities,
    list_users,
    update_activity,
    update_key_result,
    update_user,
    update_workstream,
)

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="mcp-workboard",
    version="0.7.0",
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
        "and target date.\n\n"
        "WORKSTREAMS: Use workboard_get_workstreams_tool to list accessible workstreams, "
        "workboard_get_workstream_activities_tool to see action items for a workstream, "
        "and workboard_get_team_workstreams_tool to see workstreams for a specific team.\n\n"
        "ACTION ITEMS: Use workboard_list_activities_tool to list action items with optional "
        "filters, workboard_get_activity_tool to get a single action item by ID, "
        "workboard_create_activity_tool to create a new action item, and "
        "workboard_update_activity_tool to update an existing action item's state, priority, "
        "effort, due date, or owner."
    ),
)


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


@mcp.tool()
async def workboard_get_objectives_tool(
    user_id: int,
) -> dict[str, Any]:
    """Get objectives owned by a WorkBoard user by their user ID.

    Returns all objectives the user owns, with full pagination. Also exposes
    ``workstreams`` and ``status_color`` fields on each objective when present.

    Use workboard_get_user_tool (no arguments) to find the current user's ID.
    Use workboard_get_team_members_tool to resolve a name or email to a user ID.

    Args:
        user_id: User ID (positive integer). Get this from workboard_get_user_tool.

    Returns:
        List of objectives owned by the user, including all key results
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


@mcp.tool()
async def workboard_get_workstreams_tool(
    ws_id: int | None = None,
) -> dict[str, Any]:
    """Get team workstreams accessible to the authenticated user.

    Returns all team workstreams the user has access to. Personal workstreams
    are not included. Optionally filter to a single workstream by ID.

    Args:
        ws_id: Optional workstream ID to fetch a specific workstream.

    Returns:
        List of workstreams with name, owner, health, pace, priority, and dates
    """
    return await get_workstreams(ws_id=ws_id)


@mcp.tool()
async def workboard_get_workstream_activities_tool(
    ws_id: int,
) -> dict[str, Any]:
    """Get a workstream's full details including all action items.

    Returns the workstream metadata plus every action item with descriptions,
    owners, due dates, comments, sub-actions, and attached files.

    Args:
        ws_id: Workstream ID (positive integer)

    Returns:
        Workstream details with action items
    """
    return await get_workstream_activities(ws_id=ws_id)


@mcp.tool()
async def workboard_get_team_workstreams_tool(
    team_id: int,
) -> dict[str, Any]:
    """Get all workstreams belonging to a specific team.

    Use workboard_get_teams_tool to find team IDs first.

    Args:
        team_id: Team ID (positive integer)

    Returns:
        Team info with list of workstreams
    """
    return await get_team_workstreams(team_id=team_id)


@mcp.tool()
async def workboard_create_workstream_tool(
    ws_name: str,
    team_id: str,
    ws_owner: str,
    ws_objective: str | None = None,
) -> dict[str, Any]:
    """Create a new workstream for a team.

    Requires team manager or co-manager permissions.

    Args:
        ws_name: Name of the workstream
        team_id: Parent team ID
        ws_owner: User ID of the team manager or co-manager
        ws_objective: Optional descriptive narrative or objective statement

    Returns:
        Created workstream details
    """
    return await create_workstream(
        ws_name=ws_name,
        team_id=team_id,
        ws_owner=ws_owner,
        ws_objective=ws_objective,
    )


@mcp.tool()
async def workboard_update_workstream_tool(
    ws_id: int,
    ws_name: str | None = None,
    ws_start_date: str | None = None,
    ws_end_date: str | None = None,
    ws_pace: str | None = None,
    ws_health: str | None = None,
    ws_priority: str | None = None,
) -> dict[str, Any]:
    """Update an existing workstream's properties.

    Performs read-before-write to confirm the workstream exists. Requires
    team manager or co-manager permissions. Pace must be "slow", "fast",
    or "steady". Health must be "ok", "good", or "risk". Priority must
    be "p1" through "p5".

    Args:
        ws_id: Workstream ID (positive integer)
        ws_name: New name (optional)
        ws_start_date: Start date in YYYY-MM-DD (optional)
        ws_end_date: End date in YYYY-MM-DD (optional)
        ws_pace: Pace: slow, fast, or steady (optional)
        ws_health: Health: ok, good, or risk (optional)
        ws_priority: Priority: p1 through p5 (optional)

    Returns:
        Updated workstream details
    """
    return await update_workstream(
        ws_id=ws_id,
        ws_name=ws_name,
        ws_start_date=ws_start_date,
        ws_end_date=ws_end_date,
        ws_pace=ws_pace,
        ws_health=ws_health,
        ws_priority=ws_priority,
    )


@mcp.tool()
async def workboard_list_activities_tool(
    ai_owner: str | None = None,
    ai_state: str | None = None,
    ai_priority: str | None = None,
    ai_effort: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    """List action items accessible to the authenticated user.

    Returns up to 15 action items by default. Use limit and offset for
    pagination. Filter by owner, state, priority, or effort to narrow results.

    Args:
        ai_owner: Filter by owner user ID or email (optional)
        ai_state: Filter by state: next, doing, done, or pause (optional)
        ai_priority: Filter by priority: low, med, or high (optional)
        ai_effort: Filter by effort: easy, medium, or huge (optional)
        limit: Maximum number of results (optional)
        offset: Pagination offset (optional)

    Returns:
        List of action items with descriptions, states, owners, and due dates
    """
    return await list_activities(
        ai_owner=ai_owner,
        ai_state=ai_state,
        ai_priority=ai_priority,
        ai_effort=ai_effort,
        limit=limit,
        offset=offset,
    )


@mcp.tool()
async def workboard_get_activity_tool(
    activity_id: int,
) -> dict[str, Any]:
    """Get a single WorkBoard action item by its ID.

    Args:
        activity_id: Action item ID (positive integer)

    Returns:
        Action item details including description, state, owner, due date,
        comments, sub-actions, and attached files
    """
    return await get_activity(activity_id=activity_id)


@mcp.tool()
async def workboard_create_activity_tool(
    ai_description: str,
    ai_note: str | None = None,
    ai_workstream: str | None = None,
    ai_team: str | None = None,
    ai_owner: str | None = None,
    ai_state: str | None = None,
    ai_priority: str | None = None,
    ai_effort: str | None = None,
    ai_due_date: str | None = None,
) -> dict[str, Any]:
    """Create a new action item (card) on a WorkBoard workstream.

    State must be "next", "doing", "done", or "pause".
    Priority must be "low", "med", or "high".
    Effort must be "easy", "medium", or "huge".

    Args:
        ai_description: Description of the action item — shown as the card title (required)
        ai_note: Notes or body text for the action item (optional)
        ai_workstream: Workstream ID to place the action item in (optional)
        ai_team: Team ID to associate with (optional)
        ai_owner: Owner user ID or email (optional)
        ai_state: Initial state: next, doing, done, or pause (optional)
        ai_priority: Priority: low, med, or high (optional)
        ai_effort: Effort estimate: easy, medium, or huge (optional)
        ai_due_date: Due date as UNIX timestamp string (optional)

    Returns:
        Created action item details
    """
    return await create_activity(
        ai_description=ai_description,
        ai_note=ai_note,
        ai_workstream=ai_workstream,
        ai_team=ai_team,
        ai_owner=ai_owner,
        ai_state=ai_state,
        ai_priority=ai_priority,
        ai_effort=ai_effort,
        ai_due_date=ai_due_date,
    )


@mcp.tool()
async def workboard_update_activity_tool(
    activity_id: int,
    ai_description: str | None = None,
    ai_note: str | None = None,
    ai_owner: str | None = None,
    ai_state: str | None = None,
    ai_priority: str | None = None,
    ai_effort: str | None = None,
    ai_due_date: str | None = None,
) -> dict[str, Any]:
    """Update an existing WorkBoard action item.

    Performs read-before-write to confirm the action item exists. Only
    provided fields are updated. State must be "next", "doing", "done",
    or "pause". Priority must be "low", "med", or "high". Effort must
    be "easy", "medium", or "huge".

    Args:
        activity_id: Action item ID (positive integer)
        ai_description: New description — shown as the card title (optional)
        ai_note: New notes or body text (optional)
        ai_owner: New owner user ID or email (optional)
        ai_state: New state: next, doing, done, or pause (optional)
        ai_priority: New priority: low, med, or high (optional)
        ai_effort: New effort: easy, medium, or huge (optional)
        ai_due_date: New due date as UNIX timestamp string (optional)

    Returns:
        Updated action item details
    """
    return await update_activity(
        activity_id=activity_id,
        ai_description=ai_description,
        ai_note=ai_note,
        ai_owner=ai_owner,
        ai_state=ai_state,
        ai_priority=ai_priority,
        ai_effort=ai_effort,
        ai_due_date=ai_due_date,
    )
