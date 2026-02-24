"""Tests for input validation."""

import pytest
from pydantic import ValidationError

from mcp_workboard_crunchtools.errors import InvalidObjectiveIdError, InvalidUserIdError
from mcp_workboard_crunchtools.models import (
    CreateUserInput,
    UpdateUserInput,
    validate_objective_id,
    validate_user_id,
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
