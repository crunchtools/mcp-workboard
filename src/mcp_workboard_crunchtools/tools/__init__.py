"""WorkBoard MCP tools.

This package contains all the MCP tool implementations for WorkBoard operations.
"""

from .goals import get_goal_details, get_goals
from .users import create_user, get_user, list_users, update_user

__all__ = [
    # Users
    "get_user",
    "list_users",
    "create_user",
    "update_user",
    # Goals
    "get_goals",
    "get_goal_details",
]
