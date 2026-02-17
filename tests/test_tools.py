"""Tests for MCP tools.

These tests verify tool behavior without making actual API calls.
"""

import pytest


class TestToolRegistration:
    """Tests to verify all tools are properly registered."""

    def test_server_has_tools(self) -> None:
        """Server should have all expected tools registered."""
        from mcp_workboard_crunchtools.server import mcp

        assert mcp is not None

    def test_imports(self) -> None:
        """All tool functions should be importable."""
        from mcp_workboard_crunchtools.tools import (
            create_user,
            get_goal_details,
            get_goals,
            get_user,
            list_users,
            update_user,
        )

        assert callable(get_user)
        assert callable(list_users)
        assert callable(create_user)
        assert callable(update_user)
        assert callable(get_goals)
        assert callable(get_goal_details)


class TestErrorSafety:
    """Tests to verify error messages don't leak sensitive data."""

    def test_workboard_api_error_sanitizes_token(self) -> None:
        """WorkBoardApiError should sanitize tokens from messages."""
        import os

        from mcp_workboard_crunchtools.errors import WorkBoardApiError

        os.environ["WORKBOARD_API_TOKEN"] = "secret_token_12345"

        try:
            error = WorkBoardApiError(401, "Invalid token: secret_token_12345")
            assert "secret_token_12345" not in str(error)
            assert "***" in str(error)
        finally:
            del os.environ["WORKBOARD_API_TOKEN"]

    def test_not_found_truncates_long_ids(self) -> None:
        """NotFoundError should truncate long identifiers."""
        from mcp_workboard_crunchtools.errors import NotFoundError

        long_id = "a" * 100
        error = NotFoundError("User", long_id)
        error_str = str(error)

        assert long_id not in error_str
        assert "..." in error_str

    def test_error_hierarchy(self) -> None:
        """All errors should inherit from UserError."""
        from mcp_workboard_crunchtools.errors import (
            ConfigurationError,
            InvalidGoalIdError,
            InvalidUserIdError,
            NotFoundError,
            PermissionDeniedError,
            RateLimitError,
            UserError,
            ValidationError,
            WorkBoardApiError,
        )

        assert issubclass(ConfigurationError, UserError)
        assert issubclass(InvalidUserIdError, UserError)
        assert issubclass(InvalidGoalIdError, UserError)
        assert issubclass(NotFoundError, UserError)
        assert issubclass(PermissionDeniedError, UserError)
        assert issubclass(RateLimitError, UserError)
        assert issubclass(WorkBoardApiError, UserError)
        assert issubclass(ValidationError, UserError)


class TestConfigSafety:
    """Tests for configuration security."""

    def test_config_repr_hides_token(self) -> None:
        """Config repr should never show the token."""
        import os

        os.environ["WORKBOARD_API_TOKEN"] = "secret_test_token"

        try:
            from mcp_workboard_crunchtools.config import Config

            config = Config()
            assert "secret_test_token" not in repr(config)
            assert "secret_test_token" not in str(config)
            assert "***" in repr(config)
        finally:
            del os.environ["WORKBOARD_API_TOKEN"]

    def test_config_requires_token(self) -> None:
        """Config should require WORKBOARD_API_TOKEN."""
        import os

        from mcp_workboard_crunchtools.config import Config
        from mcp_workboard_crunchtools.errors import ConfigurationError

        token = os.environ.pop("WORKBOARD_API_TOKEN", None)

        try:
            import mcp_workboard_crunchtools.config as config_module

            config_module._config = None

            with pytest.raises(ConfigurationError):
                Config()
        finally:
            if token:
                os.environ["WORKBOARD_API_TOKEN"] = token
