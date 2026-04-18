"""Tests for input validation."""

import pytest
from pydantic import ValidationError

from mcp_workboard_crunchtools.errors import (
    InvalidActivityIdError,
    InvalidMetricIdError,
    InvalidObjectiveIdError,
    InvalidTeamIdError,
    InvalidUserIdError,
    InvalidWorkstreamIdError,
    ValidationError as WBValidationError,
)
from mcp_workboard_crunchtools.models import (
    CreateActivityInput,
    CreateUserInput,
    CreateWorkstreamInput,
    UpdateActivityInput,
    UpdateUserInput,
    UpdateWorkstreamInput,
    validate_activity_id,
    validate_metric_id,
    validate_mm_dd_yyyy,
    validate_objective_id,
    validate_team_id,
    validate_user_id,
    validate_workstream_id,
)


class TestUserIdValidation:
    """Tests for user_id validation."""

    def test_valid_user_id(self) -> None:
        """Valid positive integer should pass."""
        assert validate_user_id(123) == 123

    def test_valid_user_id_large(self) -> None:
        """Large positive integer should pass."""
        assert validate_user_id(999999) == 999999

    def test_invalid_user_id_zero(self) -> None:
        """Zero should fail."""
        with pytest.raises(InvalidUserIdError):
            validate_user_id(0)

    def test_invalid_user_id_negative(self) -> None:
        """Negative integer should fail."""
        with pytest.raises(InvalidUserIdError):
            validate_user_id(-1)


class TestObjectiveIdValidation:
    """Tests for objective_id validation."""

    def test_valid_objective_id(self) -> None:
        """Valid positive integer should pass."""
        assert validate_objective_id(456) == 456

    def test_invalid_objective_id_zero(self) -> None:
        """Zero should fail."""
        with pytest.raises(InvalidObjectiveIdError):
            validate_objective_id(0)

    def test_invalid_objective_id_negative(self) -> None:
        """Negative integer should fail."""
        with pytest.raises(InvalidObjectiveIdError):
            validate_objective_id(-1)


class TestMetricIdValidation:
    """Tests for metric_id validation."""

    def test_valid_metric_id(self) -> None:
        """Valid positive integer should pass."""
        assert validate_metric_id(789) == 789

    def test_valid_metric_id_large(self) -> None:
        """Large positive integer should pass."""
        assert validate_metric_id(999999) == 999999

    def test_invalid_metric_id_zero(self) -> None:
        """Zero should fail."""
        with pytest.raises(InvalidMetricIdError):
            validate_metric_id(0)

    def test_invalid_metric_id_negative(self) -> None:
        """Negative integer should fail."""
        with pytest.raises(InvalidMetricIdError):
            validate_metric_id(-1)


class TestCreateUserInput:
    """Tests for CreateUserInput model."""

    def test_valid_user(self) -> None:
        """Valid user input should pass."""
        user = CreateUserInput(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
        )
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.email == "john.doe@example.com"
        assert user.designation is None

    def test_valid_user_with_designation(self) -> None:
        """Valid user with designation should pass."""
        user = CreateUserInput(
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            designation="VP Engineering",
        )
        assert user.designation == "VP Engineering"

    def test_invalid_email(self) -> None:
        """Invalid email should fail."""
        with pytest.raises(ValidationError):
            CreateUserInput(
                first_name="John",
                last_name="Doe",
                email="not-an-email",
            )

    def test_empty_first_name(self) -> None:
        """Empty first name should fail."""
        with pytest.raises(ValidationError):
            CreateUserInput(
                first_name="",
                last_name="Doe",
                email="john@example.com",
            )

    def test_name_too_long(self) -> None:
        """Name exceeding max length should fail."""
        with pytest.raises(ValidationError):
            CreateUserInput(
                first_name="a" * 256,
                last_name="Doe",
                email="john@example.com",
            )

    def test_extra_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            CreateUserInput(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                admin=True,  # type: ignore[call-arg]
            )


class TestUpdateUserInput:
    """Tests for UpdateUserInput model."""

    def test_partial_update(self) -> None:
        """Partial update with only some fields should pass."""
        update = UpdateUserInput(first_name="Jane")
        assert update.first_name == "Jane"
        assert update.last_name is None
        assert update.email is None
        assert update.designation is None

    def test_all_fields_none(self) -> None:
        """All fields None should be valid (checked at tool level)."""
        update = UpdateUserInput()
        assert update.first_name is None
        assert update.email is None

    def test_extra_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            UpdateUserInput(
                first_name="Jane",
                role="admin",  # type: ignore[call-arg]
            )


class TestWorkstreamIdValidation:
    """Tests for workstream_id validation."""

    def test_valid_workstream_id(self) -> None:
        """Valid positive integer should pass."""
        assert validate_workstream_id(100) == 100

    def test_valid_workstream_id_large(self) -> None:
        """Large positive integer should pass."""
        assert validate_workstream_id(999999) == 999999

    def test_invalid_workstream_id_zero(self) -> None:
        """Zero should fail."""
        with pytest.raises(InvalidWorkstreamIdError):
            validate_workstream_id(0)

    def test_invalid_workstream_id_negative(self) -> None:
        """Negative integer should fail."""
        with pytest.raises(InvalidWorkstreamIdError):
            validate_workstream_id(-1)


class TestCreateWorkstreamInput:
    """Tests for CreateWorkstreamInput model."""

    def test_valid_workstream(self) -> None:
        """Valid workstream input should pass."""
        ws = CreateWorkstreamInput(
            ws_name="Q1 Sprint",
            team_id="10",
            ws_owner="42",
        )
        assert ws.ws_name == "Q1 Sprint"
        assert ws.team_id == "10"
        assert ws.ws_owner == "42"
        assert ws.ws_objective is None

    def test_valid_workstream_with_objective(self) -> None:
        """Valid workstream with objective should pass."""
        ws = CreateWorkstreamInput(
            ws_name="Q1 Sprint",
            team_id="10",
            ws_owner="42",
            ws_objective="Ship the new feature set",
        )
        assert ws.ws_objective == "Ship the new feature set"

    def test_empty_name_rejected(self) -> None:
        """Empty name should fail."""
        with pytest.raises(ValidationError):
            CreateWorkstreamInput(
                ws_name="",
                team_id="10",
                ws_owner="42",
            )

    def test_name_too_long(self) -> None:
        """Name exceeding max length should fail."""
        with pytest.raises(ValidationError):
            CreateWorkstreamInput(
                ws_name="a" * 501,
                team_id="10",
                ws_owner="42",
            )

    def test_extra_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            CreateWorkstreamInput(
                ws_name="Sprint",
                team_id="10",
                ws_owner="42",
                ws_label="hidden",  # type: ignore[call-arg]
            )


class TestUpdateWorkstreamInput:
    """Tests for UpdateWorkstreamInput model."""

    def test_partial_update(self) -> None:
        """Partial update with only some fields should pass."""
        update = UpdateWorkstreamInput(ws_health="risk")
        assert update.ws_health == "risk"
        assert update.ws_name is None
        assert update.ws_pace is None

    def test_all_fields_none(self) -> None:
        """All fields None should be valid."""
        update = UpdateWorkstreamInput()
        assert update.ws_name is None
        assert update.ws_pace is None

    def test_valid_pace_values(self) -> None:
        """All valid pace values should pass."""
        for pace in ("slow", "fast", "steady"):
            update = UpdateWorkstreamInput(ws_pace=pace)
            assert update.ws_pace == pace

    def test_invalid_pace_rejected(self) -> None:
        """Invalid pace value should fail."""
        with pytest.raises(ValidationError):
            UpdateWorkstreamInput(ws_pace="turbo")

    def test_valid_health_values(self) -> None:
        """All valid health values should pass."""
        for health in ("ok", "good", "risk"):
            update = UpdateWorkstreamInput(ws_health=health)
            assert update.ws_health == health

    def test_invalid_health_rejected(self) -> None:
        """Invalid health value should fail."""
        with pytest.raises(ValidationError):
            UpdateWorkstreamInput(ws_health="great")

    def test_valid_priority_values(self) -> None:
        """All valid priority values should pass."""
        for priority in ("p1", "p2", "p3", "p4", "p5"):
            update = UpdateWorkstreamInput(ws_priority=priority)
            assert update.ws_priority == priority

    def test_invalid_priority_rejected(self) -> None:
        """Invalid priority value should fail."""
        with pytest.raises(ValidationError):
            UpdateWorkstreamInput(ws_priority="p0")

    def test_valid_date_format(self) -> None:
        """Valid YYYY-MM-DD date should pass."""
        update = UpdateWorkstreamInput(ws_start_date="2026-01-15")
        assert update.ws_start_date == "2026-01-15"

    def test_invalid_date_format_rejected(self) -> None:
        """Invalid date format should fail."""
        with pytest.raises(ValidationError):
            UpdateWorkstreamInput(ws_start_date="01/15/2026")

    def test_extra_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            UpdateWorkstreamInput(
                ws_health="good",
                ws_label="hidden",  # type: ignore[call-arg]
            )


class TestActivityIdValidation:
    """Tests for activity_id validation."""

    def test_valid_activity_id(self) -> None:
        """Valid positive integer should pass."""
        assert validate_activity_id(500) == 500

    def test_valid_activity_id_large(self) -> None:
        """Large positive integer should pass."""
        assert validate_activity_id(999999) == 999999

    def test_invalid_activity_id_zero(self) -> None:
        """Zero should fail."""
        with pytest.raises(InvalidActivityIdError):
            validate_activity_id(0)

    def test_invalid_activity_id_negative(self) -> None:
        """Negative integer should fail."""
        with pytest.raises(InvalidActivityIdError):
            validate_activity_id(-1)


class TestCreateActivityInput:
    """Tests for CreateActivityInput model."""

    def test_valid_minimal(self) -> None:
        """Minimal valid input (description only) should pass."""
        ai = CreateActivityInput(ai_description="Write design doc")
        assert ai.ai_description == "Write design doc"
        assert ai.ai_workstream is None
        assert ai.ai_state is None

    def test_valid_full(self) -> None:
        """Full valid input should pass."""
        ai = CreateActivityInput(
            ai_description="Review PR",
            ai_workstream="100",
            ai_team="10",
            ai_owner="alice@example.com",
            ai_state="next",
            ai_priority="high",
            ai_effort="easy",
            ai_due_date="1800000000",
            ai_column="42",
        )
        assert ai.ai_state == "next"
        assert ai.ai_priority == "high"
        assert ai.ai_effort == "easy"
        assert ai.ai_column == "42"

    def test_ai_column_defaults_none(self) -> None:
        """ai_column should default to None."""
        ai = CreateActivityInput(ai_description="Task")
        assert ai.ai_column is None

    def test_ai_column_accepts_string(self) -> None:
        """ai_column should accept any string value."""
        ai = CreateActivityInput(ai_description="Task", ai_column="99")
        assert ai.ai_column == "99"

    def test_empty_description_rejected(self) -> None:
        """Empty description should fail."""
        with pytest.raises(ValidationError):
            CreateActivityInput(ai_description="")

    def test_invalid_state_rejected(self) -> None:
        """Invalid state value should fail."""
        with pytest.raises(ValidationError):
            CreateActivityInput(ai_description="Task", ai_state="blocked")

    def test_invalid_priority_rejected(self) -> None:
        """Invalid priority value should fail."""
        with pytest.raises(ValidationError):
            CreateActivityInput(ai_description="Task", ai_priority="critical")

    def test_invalid_effort_rejected(self) -> None:
        """Invalid effort value should fail."""
        with pytest.raises(ValidationError):
            CreateActivityInput(ai_description="Task", ai_effort="gigantic")

    def test_extra_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            CreateActivityInput(
                ai_description="Task",
                ai_hidden=True,  # type: ignore[call-arg]
            )


class TestUpdateActivityInput:
    """Tests for UpdateActivityInput model."""

    def test_all_fields_none(self) -> None:
        """All fields None should be valid (empty update)."""
        update = UpdateActivityInput()
        assert update.ai_description is None
        assert update.ai_state is None

    def test_partial_update(self) -> None:
        """Partial update with only state should pass."""
        update = UpdateActivityInput(ai_state="done")
        assert update.ai_state == "done"
        assert update.ai_description is None

    def test_valid_state_values(self) -> None:
        """All valid state values should pass."""
        for state in ("next", "doing", "done", "pause"):
            update = UpdateActivityInput(ai_state=state)
            assert update.ai_state == state

    def test_invalid_state_rejected(self) -> None:
        """Invalid state value should fail."""
        with pytest.raises(ValidationError):
            UpdateActivityInput(ai_state="in_progress")

    def test_invalid_priority_rejected(self) -> None:
        """Invalid priority value should fail."""
        with pytest.raises(ValidationError):
            UpdateActivityInput(ai_priority="p1")

    def test_ai_column_defaults_none(self) -> None:
        """ai_column should default to None."""
        update = UpdateActivityInput()
        assert update.ai_column is None

    def test_ai_column_accepts_string(self) -> None:
        """ai_column should accept any string value."""
        update = UpdateActivityInput(ai_column="55")
        assert update.ai_column == "55"

    def test_extra_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            UpdateActivityInput(
                ai_state="done",
                ai_hidden=True,  # type: ignore[call-arg]
            )


class TestTeamIdValidation:
    """Tests for team_id validation."""

    def test_valid_team_id(self) -> None:
        """Valid positive integer should pass."""
        assert validate_team_id(559244) == 559244

    def test_invalid_team_id_zero(self) -> None:
        """Zero should fail."""
        with pytest.raises(InvalidTeamIdError):
            validate_team_id(0)

    def test_invalid_team_id_negative(self) -> None:
        """Negative integer should fail."""
        with pytest.raises(InvalidTeamIdError):
            validate_team_id(-5)


class TestMmDdYyyyValidation:
    """Tests for MM/DD/YYYY date string validation."""

    def test_valid_date(self) -> None:
        """Valid MM/DD/YYYY string should pass and be returned unchanged."""
        assert validate_mm_dd_yyyy("04/01/2026") == "04/01/2026"

    def test_valid_year_end(self) -> None:
        """Another valid date should pass."""
        assert validate_mm_dd_yyyy("12/31/2025", "end_date") == "12/31/2025"

    def test_iso_format_rejected(self) -> None:
        """YYYY-MM-DD (ISO) format should fail."""
        with pytest.raises(WBValidationError):
            validate_mm_dd_yyyy("2026-04-01")

    def test_partial_date_rejected(self) -> None:
        """Incomplete date should fail."""
        with pytest.raises(WBValidationError):
            validate_mm_dd_yyyy("04/2026")

    def test_non_string_rejected(self) -> None:
        """Non-string input should fail."""
        with pytest.raises(WBValidationError):
            validate_mm_dd_yyyy(20260401)  # type: ignore[arg-type]

    def test_empty_string_rejected(self) -> None:
        """Empty string should fail."""
        with pytest.raises(WBValidationError):
            validate_mm_dd_yyyy("")
