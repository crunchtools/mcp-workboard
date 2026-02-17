"""Pydantic models for input validation.

All tool inputs are validated through these models to prevent injection attacks
and ensure data integrity before making API calls.

WorkBoard IDs are positive integers (not hex strings like Cloudflare).
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .errors import InvalidGoalIdError, InvalidUserIdError


def validate_user_id(user_id: int) -> int:
    """Validate a user ID is a positive integer."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise InvalidUserIdError
    return user_id


def validate_goal_id(goal_id: int) -> int:
    """Validate a goal ID is a positive integer."""
    if not isinstance(goal_id, int) or goal_id <= 0:
        raise InvalidGoalIdError
    return goal_id


class CreateUserInput(BaseModel):
    """Validated input for creating a new WorkBoard user."""

    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(
        ..., min_length=1, max_length=255, description="User's first name"
    )
    last_name: str = Field(
        ..., min_length=1, max_length=255, description="User's last name"
    )
    email: EmailStr = Field(
        ..., description="User's email address"
    )
    designation: str | None = Field(
        default=None, max_length=255, description="User's job title or designation"
    )


class UpdateUserInput(BaseModel):
    """Validated input for updating an existing WorkBoard user.

    All fields are optional - only provided fields will be updated.
    """

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(
        default=None, min_length=1, max_length=255, description="User's first name"
    )
    last_name: str | None = Field(
        default=None, min_length=1, max_length=255, description="User's last name"
    )
    email: EmailStr | None = Field(
        default=None, description="User's email address"
    )
    designation: str | None = Field(
        default=None, max_length=255, description="User's job title or designation"
    )
