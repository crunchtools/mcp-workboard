"""Tests for input validation."""

import pytest
from pydantic import ValidationError

from mcp_workboard_crunchtools.errors import (
    InvalidMetricIdError,
    InvalidObjectiveIdError,
    InvalidUserIdError,
    InvalidWorkstreamIdError,
)
from mcp_workboard_crunchtools.models import (
    CreateUserInput,
    CreateWorkstreamInput,
    UpdateUserInput,
    UpdateWorkstreamInput,
    validate_metric_id,
    validate_objective_id,
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
