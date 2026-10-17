"""User management tools.

Tools for getting, listing, creating, and updating WorkBoard users.
"""

from typing import Any, Literal

from ..client import get_client
from ..models import CreateUserInput, UpdateUserInput, validate_user_id


async def get_user(
    user_id: int | None = None,
) -> dict[str, Any]:
    """Get a WorkBoard user by ID, or the current authenticated user.

    Args:
        user_id: User ID (positive integer). If not provided, returns the
                 current authenticated user.

    Returns:
        User details dictionary
    """
    client = get_client()

    if user_id is not None:
        user_id = validate_user_id(user_id)
        response = await client.get(f"/user/{user_id}")
    else:
        response = await client.get("/user")

    return {"user": response}


async def list_users(
    scope: Literal["team", "org"] = "team",
    limit: int = 100,
    offset: int | None = None,
) -> dict[str, Any]:
    """List WorkBoard users.

    Bare GET /user returns only the caller. include=team_members returns the
    members of teams the caller can see and works for any token;
    include=org_members returns the whole organization but needs a
    Data-Admin token (WorkBoard answers 400 otherwise).

    Args:
        scope: "team" for members of the caller's teams, "org" for every user
               in the organization (Data-Admin only)
        limit: Maximum number of users to return (default 100)
        offset: Number of users to skip (optional)

    Returns:
        Dictionary containing list of users
    """
    client = get_client()

    if scope == "org":
        params: dict[str, Any] = {"include": "org_members", "limit": limit}
        if offset is not None:
            params["offset"] = offset
        response = await client.get("/user", params=params)
        return {"users": response}

    # team_members is not paginated by the API, so page it here.
    response = await client.get("/user", params={"include": "team_members"})
    team_listing = response.get("data")
    if isinstance(team_listing, dict) and isinstance(team_listing.get("user"), list):
        start = offset or 0
        team_listing["user"] = team_listing["user"][start : start + limit]

    return {"users": response}


async def create_user(
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
    user_input = CreateUserInput(
        first_name=first_name,
        last_name=last_name,
        email=email,
        designation=designation,
    )

    client = get_client()

    body: dict[str, Any] = {
        "first_name": user_input.first_name,
        "last_name": user_input.last_name,
        "email": user_input.email,
    }

    if user_input.designation is not None:
        body["designation"] = user_input.designation

    response = await client.post("/user", json_data=body)

    return {"user": response}


async def update_user(
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
    user_id = validate_user_id(user_id)

    update_input = UpdateUserInput(
        first_name=first_name,
        last_name=last_name,
        email=email,
        designation=designation,
    )

    client = get_client()

    body: dict[str, Any] = {}

    if update_input.first_name is not None:
        body["first_name"] = update_input.first_name
    if update_input.last_name is not None:
        body["last_name"] = update_input.last_name
    if update_input.email is not None:
        body["email"] = update_input.email
    if update_input.designation is not None:
        body["designation"] = update_input.designation

    if not body:
        return {"error": "No fields provided for update"}

    response = await client.put(f"/user/{user_id}", json_data=body)

    return {"user": response}
