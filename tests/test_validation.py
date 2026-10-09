"""Tests for input validation."""

import pytest
from pydantic import ValidationError

from mcp_workboard_crunchtools.errors import (
    InvalidActivityIdError,
    InvalidMetricIdError,
    InvalidObjectiveIdError,
    InvalidUserIdError,
    InvalidWorkstreamIdError,
)
from mcp_workboard_crunchtools.models import (
    CreateActivityInput,
    CreateObjectiveInput,
    CreateUserInput,
    CreateWorkstreamInput,
    KeyResultInput,
    UpdateActivityInput,
    UpdateUserInput,
    UpdateWorkstreamInput,
    metric_unit_code,
    validate_activity_id,
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


class TestCreateObjectiveInput:
    """Tests for CreateObjectiveInput model."""

    def _base(self, **overrides: str) -> dict[str, str]:
        data = {
            "name": "Objective",
            "owner": "owner@example.com",
            "start_date": "2026-01-01",
            "target_date": "2026-12-31",
        }
        data.update(overrides)
        return data

    def test_defaults(self) -> None:
        """objective_type defaults to team ('1'), permission to a valid team value."""
        obj = CreateObjectiveInput(**self._base())
        assert obj.objective_type == "1"
        assert obj.permission == "internal,team"
        assert obj.team is None

    def test_individual_permission_default_is_owner(self) -> None:
        """Individual objectives default to 'owner' — the API rejects 'internal' here."""
        obj = CreateObjectiveInput(**self._base(objective_type="individual"))
        assert obj.objective_type == "2"
        assert obj.permission == "owner"

    def test_explicit_permission_is_preserved(self) -> None:
        """An explicitly supplied permission overrides the type default."""
        obj = CreateObjectiveInput(**self._base(objective_type="individual", permission="manager"))
        assert obj.permission == "manager"

    def test_blank_permission_normalizes_to_type_default(self) -> None:
        """Whitespace-only permission is treated as unset, then defaulted by type."""
        obj = CreateObjectiveInput(**self._base(permission="   "))
        assert obj.permission == "internal,team"

    def test_blank_team_normalizes_to_none(self) -> None:
        """Whitespace-only team becomes None (profile §I)."""
        assert CreateObjectiveInput(**self._base(team="  ")).team is None
        assert CreateObjectiveInput(**self._base(team="561838")).team == "561838"

    def test_objective_type_accepts_words_and_numbers(self) -> None:
        """team/individual (any case) and 1/2 all normalize to the API encoding."""
        assert CreateObjectiveInput(**self._base(objective_type="team")).objective_type == "1"
        assert CreateObjectiveInput(**self._base(objective_type="Individual")).objective_type == "2"
        assert CreateObjectiveInput(**self._base(objective_type="1")).objective_type == "1"
        assert CreateObjectiveInput(**self._base(objective_type="2")).objective_type == "2"

    def test_invalid_objective_type_rejected(self) -> None:
        """An unknown objective_type is rejected with a clean message."""
        with pytest.raises(ValidationError) as exc:
            CreateObjectiveInput(**self._base(objective_type="squad"))
        assert "objective_type" in str(exc.value)
        assert "goal_type" not in str(exc.value)

    def test_invalid_date_rejected(self) -> None:
        """Dates must be YYYY-MM-DD."""
        with pytest.raises(ValidationError):
            CreateObjectiveInput(**self._base(start_date="01/01/2026"))

    def test_extra_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            CreateObjectiveInput(**self._base(goal_type="1"))


class TestKeyResultInput:
    """Tests for KeyResultInput model."""

    def test_name_only_is_valid(self) -> None:
        """A key result needs only a name; the rest default to None."""
        kr = KeyResultInput(name="Ship it")
        assert kr.name == "Ship it"
        assert kr.start_value is None
        assert kr.target_value is None
        assert kr.unit_type is None

    def test_blank_optionals_normalize_to_none(self) -> None:
        """Empty/whitespace optionals become None (profile §I)."""
        kr = KeyResultInput(name="Ship it", start_value="  ", target_value="")
        assert kr.start_value is None
        assert kr.target_value is None

    def test_empty_name_rejected(self) -> None:
        """Name is required and non-empty."""
        with pytest.raises(ValidationError):
            KeyResultInput(name="")

    def test_overlong_value_rejected(self) -> None:
        """Numeric value strings are length-bounded (constitution)."""
        with pytest.raises(ValidationError):
            KeyResultInput(name="Ship it", target_value="9" * 100)

    def test_unit_code_mapping(self) -> None:
        """UI unit names map to the API's numeric metric_unit; unknown falls back to number."""
        assert metric_unit_code("Number") == "1"
        assert metric_unit_code("currency") == "2"
        assert metric_unit_code("Percent") == "3"
        assert metric_unit_code("%") == "3"
        assert metric_unit_code(None) == "1"
        assert metric_unit_code("gibberish") == "1"

    def test_extra_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            KeyResultInput(name="Ship it", metric_name="legacy")  # type: ignore[call-arg]
