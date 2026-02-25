"""Pydantic models for input validation.

All tool inputs are validated through these models to prevent injection attacks
and ensure data integrity before making API calls.

WorkBoard IDs are positive integers (not hex strings like Cloudflare).
"""

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .errors import InvalidMetricIdError, InvalidObjectiveIdError, InvalidUserIdError


def validate_user_id(user_id: int) -> int:
    """Validate a user ID is a positive integer."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise InvalidUserIdError
    return user_id


def validate_objective_id(objective_id: int) -> int:
    """Validate an objective ID is a positive integer."""
    if not isinstance(objective_id, int) or objective_id <= 0:
        raise InvalidObjectiveIdError
    return objective_id


def validate_metric_id(metric_id: int) -> int:
    """Validate a metric ID is a positive integer."""
    if not isinstance(metric_id, int) or metric_id <= 0:
        raise InvalidMetricIdError
    return metric_id


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


# Date format pattern for YYYY-MM-DD
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class UpdateKeyResultInput(BaseModel):
    """Validated input for updating a key result (metric).

    Ensures the value is a non-negative number and comments are bounded.
    """

    model_config = ConfigDict(extra="forbid")

    value: str = Field(
        ..., min_length=1, max_length=20, description="Progress value (non-negative number)"
    )
    comment: str | None = Field(
        default=None, max_length=1000, description="Optional check-in comment"
    )

    @field_validator("value")
    @classmethod
    def value_must_be_non_negative_number(cls, v: str) -> str:
        """Validate that value is a non-negative number."""
        try:
            num = float(v)
        except ValueError as err:
            raise ValueError(f"Value must be a number, got: {v!r}") from err
        if num < 0:
            raise ValueError(f"Value must be non-negative, got: {num}")
        return v


class CreateObjectiveInput(BaseModel):
    """Validated input for creating a new objective.

    Matches the validation rigor used for user creation tools.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ..., min_length=1, max_length=500, description="Objective name"
    )
    owner: str = Field(
        ..., min_length=1, max_length=255, description="Owner email or user ID"
    )
    start_date: str = Field(
        ..., description="Start date in YYYY-MM-DD format"
    )
    target_date: str = Field(
        ..., description="Target date in YYYY-MM-DD format"
    )
    narrative: str | None = Field(
        default=None, max_length=2000, description="Objective description"
    )
    goal_type: str = Field(
        default="1", description="1=Team, 2=Personal"
    )
    permission: str = Field(
        default="internal,team", max_length=100, description="Visibility setting"
    )

    @field_validator("start_date", "target_date")
    @classmethod
    def date_must_be_valid_format(cls, v: str) -> str:
        """Validate date is YYYY-MM-DD format."""
        if not _DATE_RE.match(v):
            raise ValueError(f"Date must be YYYY-MM-DD format, got: {v!r}")
        return v

    @field_validator("goal_type")
    @classmethod
    def goal_type_must_be_valid(cls, v: str) -> str:
        """Validate goal_type is 1 or 2."""
        if v not in ("1", "2"):
            raise ValueError(f"goal_type must be '1' (Team) or '2' (Personal), got: {v!r}")
        return v
