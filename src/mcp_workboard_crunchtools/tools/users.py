"""User management tools.

Tools for getting, listing, creating, and updating WorkBoard users.
"""

from typing import Any

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


async def list_users() -> dict[str, Any]:
    """List all WorkBoard users (requires Data-Admin role).

    Returns:
        Dictionary containing list of all users
    """
    client = get_client()

    response = await client.get("/user")

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
    # Validate input using Pydantic model
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

    # Validate input using Pydantic model
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
