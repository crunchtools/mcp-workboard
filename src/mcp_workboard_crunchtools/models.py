"""Pydantic models for input validation."""

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .errors import (
    InvalidActivityIdError,
    InvalidMetricIdError,
    InvalidObjectiveIdError,
    InvalidUserIdError,
    InvalidWorkstreamIdError,
)

MAX_NAME_LENGTH = 255
MAX_OBJECTIVE_NAME_LENGTH = 500
MAX_VALUE_LENGTH = 20
MAX_COMMENT_LENGTH = 1000
MAX_NARRATIVE_LENGTH = 2000
MAX_PERMISSION_LENGTH = 100


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


def validate_workstream_id(workstream_id: int) -> int:
    """Validate a workstream ID is a positive integer."""
    if not isinstance(workstream_id, int) or workstream_id <= 0:
        raise InvalidWorkstreamIdError
    return workstream_id


def validate_activity_id(activity_id: int) -> int:
    """Validate an activity ID is a positive integer."""
    if not isinstance(activity_id, int) or activity_id <= 0:
        raise InvalidActivityIdError
    return activity_id


class CreateUserInput(BaseModel):
    """Validated input for creating a new WorkBoard user."""

    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(
        ..., min_length=1, max_length=MAX_NAME_LENGTH, description="User's first name"
    )
    last_name: str = Field(
        ..., min_length=1, max_length=MAX_NAME_LENGTH, description="User's last name"
    )
    email: EmailStr = Field(..., description="User's email address")
    designation: str | None = Field(
        default=None, max_length=MAX_NAME_LENGTH, description="User's job title or designation"
    )


class UpdateUserInput(BaseModel):
    """Validated input for updating an existing WorkBoard user.

    All fields are optional - only provided fields will be updated.
    """

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(
        default=None, min_length=1, max_length=MAX_NAME_LENGTH, description="User's first name"
    )
    last_name: str | None = Field(
        default=None, min_length=1, max_length=MAX_NAME_LENGTH, description="User's last name"
    )
    email: EmailStr | None = Field(default=None, description="User's email address")
    designation: str | None = Field(
        default=None, max_length=MAX_NAME_LENGTH, description="User's job title or designation"
    )


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class UpdateKeyResultInput(BaseModel):
    """Validated input for updating a key result (metric).

    Ensures the value is a non-negative number and comments are bounded.
    """

    model_config = ConfigDict(extra="forbid")

    value: str = Field(
        ...,
        min_length=1,
        max_length=MAX_VALUE_LENGTH,
        description="Progress value (non-negative number)",
    )
    comment: str | None = Field(
        default=None, max_length=MAX_COMMENT_LENGTH, description="Optional check-in comment"
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
        ..., min_length=1, max_length=MAX_OBJECTIVE_NAME_LENGTH, description="Objective name"
    )
    owner: str = Field(
        ..., min_length=1, max_length=MAX_NAME_LENGTH, description="Owner email or user ID"
    )
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    target_date: str = Field(..., description="Target date in YYYY-MM-DD format")
    narrative: str | None = Field(
        default=None, max_length=MAX_NARRATIVE_LENGTH, description="Objective description"
    )
    goal_type: str = Field(default="1", description="1=Team, 2=Personal")
    permission: str = Field(
        default="internal,team",
        max_length=MAX_PERMISSION_LENGTH,
        description="Visibility setting",
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


MAX_WORKSTREAM_NAME_LENGTH = 500
MAX_WORKSTREAM_OBJECTIVE_LENGTH = 2000

_VALID_PACE = {"slow", "fast", "steady"}
_VALID_HEALTH = {"ok", "good", "risk"}
_VALID_PRIORITY = {"p1", "p2", "p3", "p4", "p5"}


class CreateWorkstreamInput(BaseModel):
    """Validated input for creating a new workstream."""

    model_config = ConfigDict(extra="forbid")

    ws_name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_WORKSTREAM_NAME_LENGTH,
        description="Name of the workstream",
    )
    ws_objective: str | None = Field(
        default=None,
        max_length=MAX_WORKSTREAM_OBJECTIVE_LENGTH,
        description="Descriptive narrative or objective statement",
    )
    team_id: str = Field(
        ...,
        min_length=1,
        description="Parent team ID",
    )
    ws_owner: str = Field(
        ...,
        min_length=1,
        description="User ID of the team manager or co-manager",
    )


class UpdateWorkstreamInput(BaseModel):
    """Validated input for updating an existing workstream.

    All fields are optional — only provided fields will be sent.
    """

    model_config = ConfigDict(extra="forbid")

    ws_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_WORKSTREAM_NAME_LENGTH,
        description="Name of the workstream",
    )
    ws_start_date: str | None = Field(
        default=None,
        description="Start date (YYYY-MM-DD)",
    )
    ws_end_date: str | None = Field(
        default=None,
        description="End date (YYYY-MM-DD)",
    )
    ws_pace: str | None = Field(
        default=None,
        description="Pace: slow, fast, or steady",
    )
    ws_health: str | None = Field(
        default=None,
        description="Health: ok, good, or risk",
    )
    ws_priority: str | None = Field(
        default=None,
        description="Priority: p1 through p5",
    )

    @field_validator("ws_start_date", "ws_end_date")
    @classmethod
    def date_must_be_valid_format(cls, v: str | None) -> str | None:
        """Validate date is YYYY-MM-DD format when provided."""
        if v is not None and not _DATE_RE.match(v):
            raise ValueError(f"Date must be YYYY-MM-DD format, got: {v!r}")
        return v

    @field_validator("ws_pace")
    @classmethod
    def pace_must_be_valid(cls, v: str | None) -> str | None:
        """Validate pace is one of the allowed values."""
        if v is not None and v not in _VALID_PACE:
            raise ValueError(f"ws_pace must be one of {sorted(_VALID_PACE)}, got: {v!r}")
        return v

    @field_validator("ws_health")
    @classmethod
    def health_must_be_valid(cls, v: str | None) -> str | None:
        """Validate health is one of the allowed values."""
        if v is not None and v not in _VALID_HEALTH:
            raise ValueError(f"ws_health must be one of {sorted(_VALID_HEALTH)}, got: {v!r}")
        return v

    @field_validator("ws_priority")
    @classmethod
    def priority_must_be_valid(cls, v: str | None) -> str | None:
        """Validate priority is one of the allowed values."""
        if v is not None and v not in _VALID_PRIORITY:
            raise ValueError(f"ws_priority must be one of {sorted(_VALID_PRIORITY)}, got: {v!r}")
        return v


MAX_ACTIVITY_DESCRIPTION_LENGTH = 500

_VALID_AI_STATE = {"next", "doing", "done", "pause"}
_VALID_AI_PRIORITY = {"low", "med", "high"}
_VALID_AI_EFFORT = {"easy", "medium", "huge"}


def _validate_ai_state(v: str | None) -> str | None:
    """Validate activity state is one of the allowed values."""
    if v is not None and v not in _VALID_AI_STATE:
        raise ValueError(f"ai_state must be one of {sorted(_VALID_AI_STATE)}, got: {v!r}")
    return v


def _validate_ai_priority(v: str | None) -> str | None:
    """Validate activity priority is one of the allowed values."""
    if v is not None and v not in _VALID_AI_PRIORITY:
        raise ValueError(f"ai_priority must be one of {sorted(_VALID_AI_PRIORITY)}, got: {v!r}")
    return v


def _validate_ai_effort(v: str | None) -> str | None:
    """Validate activity effort is one of the allowed values."""
    if v is not None and v not in _VALID_AI_EFFORT:
        raise ValueError(f"ai_effort must be one of {sorted(_VALID_AI_EFFORT)}, got: {v!r}")
    return v


class CreateActivityInput(BaseModel):
    """Validated input for creating a new action item (activity)."""

    model_config = ConfigDict(extra="forbid")

    ai_description: str = Field(
        ...,
        min_length=1,
        max_length=MAX_ACTIVITY_DESCRIPTION_LENGTH,
        description="Description of the action item",
    )
    ai_note: str | None = Field(default=None, description="Notes or body text for the action item")
    ai_workstream: str | None = Field(default=None, min_length=1, description="Workstream ID")
    ai_team: str | None = Field(default=None, min_length=1, description="Team ID")
    ai_owner: str | None = Field(default=None, min_length=1, description="Owner user ID or email")
    ai_state: str | None = Field(default=None, description="State: next, doing, done, or pause")
    ai_priority: str | None = Field(default=None, description="Priority: low, med, or high")
    ai_effort: str | None = Field(default=None, description="Effort: easy, medium, or huge")
    ai_due_date: str | None = Field(
        default=None, min_length=1, description="Due date as UNIX timestamp string"
    )

    @field_validator("ai_state")
    @classmethod
    def state_must_be_valid(cls, v: str | None) -> str | None:
        return _validate_ai_state(v)

    @field_validator("ai_priority")
    @classmethod
    def priority_must_be_valid_ai(cls, v: str | None) -> str | None:
        return _validate_ai_priority(v)

    @field_validator("ai_effort")
    @classmethod
    def effort_must_be_valid(cls, v: str | None) -> str | None:
        return _validate_ai_effort(v)


class UpdateActivityInput(BaseModel):
    """Validated input for updating an existing action item.

    All fields are optional — only provided fields will be sent.
    """

    model_config = ConfigDict(extra="forbid")

    ai_description: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_ACTIVITY_DESCRIPTION_LENGTH,
        description="Description of the action item",
    )
    ai_note: str | None = Field(default=None, description="Notes or body text for the action item")
    ai_owner: str | None = Field(default=None, min_length=1, description="Owner user ID or email")
    ai_state: str | None = Field(default=None, description="State: next, doing, done, or pause")
    ai_priority: str | None = Field(default=None, description="Priority: low, med, or high")
    ai_effort: str | None = Field(default=None, description="Effort: easy, medium, or huge")
    ai_due_date: str | None = Field(
        default=None, min_length=1, description="Due date as UNIX timestamp string"
    )

    @field_validator("ai_state")
    @classmethod
    def state_must_be_valid(cls, v: str | None) -> str | None:
        return _validate_ai_state(v)

    @field_validator("ai_priority")
    @classmethod
    def priority_must_be_valid_ai(cls, v: str | None) -> str | None:
        return _validate_ai_priority(v)

    @field_validator("ai_effort")
    @classmethod
    def effort_must_be_valid(cls, v: str | None) -> str | None:
        return _validate_ai_effort(v)
