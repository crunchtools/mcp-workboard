"""WorkBoard MCP tools.

This package contains all the MCP tool implementations for WorkBoard operations.
"""

from .activities import (
    create_activity,
    get_activity,
    list_activities,
    update_activity,
)
from .objectives import (
    create_objective,
    get_my_key_results,
    get_my_objectives,
    get_objective_details,
    get_objectives,
    get_team_objectives,
    get_user_key_results,
    update_key_result,
)
from .teams import get_team_members, get_teams
from .users import create_user, get_user, list_users, update_user
from .workstreams import (
    create_workstream,
    get_team_workstreams,
    get_workstream_activities,
    get_workstreams,
    update_workstream,
)

__all__ = [
    "list_activities",
    "get_activity",
    "create_activity",
    "update_activity",
    "get_user",
    "list_users",
    "create_user",
    "update_user",
    "get_teams",
    "get_team_members",
    "get_objectives",
    "get_objective_details",
    "get_my_objectives",
    "get_my_key_results",
    "get_user_key_results",
    "get_team_objectives",
    "update_key_result",
    "create_objective",
    "get_workstreams",
    "get_workstream_activities",
    "get_team_workstreams",
    "create_workstream",
    "update_workstream",
]
