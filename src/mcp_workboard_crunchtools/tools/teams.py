"""WorkBoard team tools."""

from __future__ import annotations

from typing import Any

from ..client import get_client


def _format_team(team: dict[str, Any]) -> dict[str, Any]:
    """Format a raw team object for MCP output."""
    return {
        "team_id": int(team.get("team_id", 0)),
        "team_name": team.get("team_name", ""),
        "team_owner_id": team.get("team_owner"),  # numeric user_id of team owner
        "is_team_owner": bool(team.get("is_team_owner", False)),
    }


def _format_team_member(member: dict[str, Any]) -> dict[str, Any]:
    """Format a raw team member object for MCP output."""
    return {
        "user_id": int(member.get("id", 0)),
        "first_name": member.get("first_name", ""),
        "last_name": member.get("last_name", ""),
        "full_name": f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
        "email": member.get("email", ""),
        "team_role": member.get("team_role", ""),
    }


async def get_teams() -> dict[str, Any]:
    """Fetch all teams the authenticated user belongs to."""
    client = get_client()
    response = await client.get("/team")

    if isinstance(response, list):
        teams = response
    elif isinstance(response, dict):
        teams = (
            response.get("teams")
            or response.get("data", {}).get("teams")
            or response.get("data", {}).get("team")
            or []
        )
        if isinstance(teams, dict):
                teams = list(teams.values())
    else:
        teams = []

    return {"teams": [_format_team(t) for t in teams if isinstance(t, dict)]}


async def get_team_members(team_id: int) -> dict[str, Any]:
    """Fetch all members of a specific team by team_id."""
    client = get_client()
    response = await client.get(f"/team/{team_id}/user")

    if isinstance(response, dict):
        team_data = (
            response.get("data", {}).get("team")
            or response.get("team")
            or {}
        )
        members = team_data.get("team_members", [])
        team_name = team_data.get("team_name", "")
    else:
        members = []
        team_name = ""

    if not isinstance(members, list):
        members = []

    return {
        "team_id": team_id,
        "team_name": team_name,
        "members": [_format_team_member(m) for m in members if isinstance(m, dict)],
    }
