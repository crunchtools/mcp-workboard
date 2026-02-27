"""Tests for MCP tools.

These tests verify tool behavior without making actual API calls.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest


class TestToolRegistration:
    """Tests to verify all tools are properly registered."""

    def test_server_has_tools(self) -> None:
        """Server should have all expected tools registered."""
        from mcp_workboard_crunchtools.server import mcp

        assert mcp is not None

    def test_tool_count(self) -> None:
        """Server should have exactly 13 tools registered."""
        from mcp_workboard_crunchtools.tools import __all__

        assert len(__all__) == 13

    def test_imports(self) -> None:
        """All tool functions should be importable."""
        import mcp_workboard_crunchtools.tools as tools_mod
        from mcp_workboard_crunchtools.tools import __all__

        for name in __all__:
            func = getattr(tools_mod, name)
            assert callable(func), f"{name} is not callable"


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
            InvalidMetricIdError,
            InvalidObjectiveIdError,
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
        assert issubclass(InvalidObjectiveIdError, UserError)
        assert issubclass(InvalidMetricIdError, UserError)
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



def _mock_response(
    status_code: int = 200,
    json_data: dict | list | None = None,
) -> httpx.Response:
    """Build a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        headers={"content-type": "application/json"},
        json=json_data if json_data is not None else {},
        request=httpx.Request("GET", "https://www.myworkboard.com/wb/apis/test"),
    )


@pytest.fixture(autouse=True)
def _reset_client_singleton():
    """Reset the global client and config singletons between tests."""
    import mcp_workboard_crunchtools.client as client_mod
    import mcp_workboard_crunchtools.config as config_mod

    client_mod._client = None
    config_mod._config = None
    yield
    client_mod._client = None
    config_mod._config = None


def _patch_client(mock_response: httpx.Response):
    """Patch the httpx AsyncClient to return a mock response.

    Sets WORKBOARD_API_TOKEN so config initializes, then mocks the HTTP layer.
    """
    import os

    import mcp_workboard_crunchtools.client as client_mod
    import mcp_workboard_crunchtools.config as config_mod

    client_mod._client = None
    config_mod._config = None

    os.environ.setdefault("WORKBOARD_API_TOKEN", "test-mock-token")

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.request = AsyncMock(return_value=mock_response)

    return patch.object(
        httpx, "AsyncClient", return_value=mock_http,
    )



class TestUserTools:
    """Tests for user tools with mocked API responses."""

    @pytest.mark.asyncio
    async def test_get_user(self) -> None:
        """get_user should return user data."""
        from mcp_workboard_crunchtools.tools import get_user

        resp = _mock_response(json_data={
            "data": {"user": {"user_id": "12345", "first_name": "Scott"}},
        })

        with _patch_client(resp):
            result = await get_user()

        assert "user" in result

    @pytest.mark.asyncio
    async def test_get_user_by_id(self) -> None:
        """get_user with user_id should fetch specific user."""
        from mcp_workboard_crunchtools.tools import get_user

        resp = _mock_response(json_data={
            "data": {"user": {"user_id": "99", "first_name": "Gunnar"}},
        })

        with _patch_client(resp):
            result = await get_user(user_id=99)

        assert "user" in result

    @pytest.mark.asyncio
    async def test_list_users(self) -> None:
        """list_users should return users list."""
        from mcp_workboard_crunchtools.tools import list_users

        resp = _mock_response(json_data={
            "data": [
                {"user_id": "1", "first_name": "Alice"},
                {"user_id": "2", "first_name": "Bob"},
            ],
        })

        with _patch_client(resp):
            result = await list_users()

        assert "users" in result

    @pytest.mark.asyncio
    async def test_create_user(self) -> None:
        """create_user should post and return created user."""
        from mcp_workboard_crunchtools.tools import create_user

        resp = _mock_response(json_data={
            "data": {"user": {"user_id": "100", "first_name": "New"}},
        })

        with _patch_client(resp):
            result = await create_user(
                first_name="New",
                last_name="User",
                email="new@example.com",
            )

        assert "user" in result

    @pytest.mark.asyncio
    async def test_update_user(self) -> None:
        """update_user should put and return updated user."""
        from mcp_workboard_crunchtools.tools import update_user

        resp = _mock_response(json_data={
            "data": {"user": {"user_id": "42", "first_name": "Updated"}},
        })

        with _patch_client(resp):
            result = await update_user(user_id=42, first_name="Updated")

        assert "user" in result


class TestTeamTools:
    """Tests for team tools with mocked API responses."""

    @pytest.mark.asyncio
    async def test_get_teams(self) -> None:
        """get_teams should return formatted team list."""
        from mcp_workboard_crunchtools.tools import get_teams

        resp = _mock_response(json_data={
            "data": {
                "teams": [
                    {"team_id": 10, "team_name": "Engineering", "team_owner": 1},
                ],
            },
        })

        with _patch_client(resp):
            result = await get_teams()

        assert "teams" in result
        assert len(result["teams"]) == 1
        assert result["teams"][0]["team_name"] == "Engineering"

    @pytest.mark.asyncio
    async def test_get_team_members(self) -> None:
        """get_team_members should return formatted member list."""
        from mcp_workboard_crunchtools.tools import get_team_members

        resp = _mock_response(json_data={
            "data": {
                "team": {
                    "team_name": "Engineering",
                    "team_members": [
                        {"id": 1, "first_name": "Alice", "last_name": "Smith", "email": "a@ex.com"},
                    ],
                },
            },
        })

        with _patch_client(resp):
            result = await get_team_members(team_id=10)

        assert result["team_id"] == 10
        assert result["team_name"] == "Engineering"
        assert len(result["members"]) == 1
        assert result["members"][0]["full_name"] == "Alice Smith"


class TestObjectiveTools:
    """Tests for objective tools with mocked API responses."""

    @pytest.mark.asyncio
    async def test_get_objectives(self) -> None:
        """get_objectives should return formatted objectives."""
        from mcp_workboard_crunchtools.tools import get_objectives

        resp = _mock_response(json_data={
            "data": {
                "goal_count": 1,
                "user": {
                    "goal": {
                        "0": {
                            "goal_id": 100,
                            "goal_name": "Ship v1",
                            "goal_progress": "75",
                            "goal_metrics": [],
                        },
                    },
                },
                "metric": [],
            },
        })

        with _patch_client(resp):
            result = await get_objectives(user_id=42)

        assert "objectives" in result
        assert len(result["objectives"]) == 1
        assert result["objectives"][0]["name"] == "Ship v1"

    @pytest.mark.asyncio
    async def test_get_objective_details(self) -> None:
        """get_objective_details should return single objective with KRs."""
        from mcp_workboard_crunchtools.tools import get_objective_details

        resp = _mock_response(json_data={
            "data": {
                "user": {
                    "goal": {
                        "goal_id": 200,
                        "goal_name": "Retention",
                        "goal_progress": "50",
                        "goal_metrics": [
                            {
                                "metric_id": 300,
                                "metric_name": "NPS Score",
                                "metric_target": "80",
                                "metric_achieve_target": "40",
                                "metric_unit": {"name": "Number"},
                            },
                        ],
                    },
                },
                "metric": [],
            },
        })

        with _patch_client(resp):
            result = await get_objective_details(user_id=42, objective_id=200)

        assert "objective" in result
        assert result["objective"]["name"] == "Retention"
        assert len(result["objective"]["key_results"]) == 1

    @pytest.mark.asyncio
    async def test_get_my_objectives(self) -> None:
        """get_my_objectives should auto-discover from metrics."""
        from mcp_workboard_crunchtools.tools import get_my_objectives

        user_resp = _mock_response(json_data={
            "data": {"user": {"user_id": "42"}},
        })
        metric_resp = _mock_response(json_data={
            "data": {
                "metric": [
                    {"metric_id": 10, "metric_goal_id": 100, "target_date": "2000000000"},
                ],
            },
        })
        goal_resp = _mock_response(json_data={
            "data": {
                "user": {
                    "goal": {
                        "goal_id": 100,
                        "goal_name": "My OKR",
                        "goal_progress": "60",
                        "goal_metrics": [],
                    },
                },
            },
        })

        import os

        import mcp_workboard_crunchtools.client as client_mod
        import mcp_workboard_crunchtools.config as config_mod

        client_mod._client = None
        config_mod._config = None
        os.environ.setdefault("WORKBOARD_API_TOKEN", "test-mock-token")

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        call_count = 0

        async def side_effect(**kwargs):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            url = str(kwargs.get("url", ""))
            if url == "/user" and kwargs.get("method") == "GET":
                return user_resp
            if "/metric" in url:
                return metric_resp
            return goal_resp

        mock_http.request = AsyncMock(side_effect=side_effect)

        with patch.object(httpx, "AsyncClient", return_value=mock_http):
            result = await get_my_objectives()

        assert "objectives" in result

    @pytest.mark.asyncio
    async def test_create_objective(self) -> None:
        """create_objective should post and return created objective."""
        from mcp_workboard_crunchtools.tools import create_objective

        resp = _mock_response(json_data={
            "data": {"goal": {"goal_id": 500, "goal_name": "New Goal"}},
        })

        with _patch_client(resp):
            result = await create_objective(
                name="New Goal",
                owner="owner@example.com",
                start_date="2026-01-01",
                target_date="2026-12-31",
            )

        assert "objective" in result


class TestKeyResultTools:
    """Tests for key result tools with mocked API responses."""

    @pytest.mark.asyncio
    async def test_get_my_key_results(self) -> None:
        """get_my_key_results should return formatted metrics."""
        from mcp_workboard_crunchtools.tools import get_my_key_results

        resp = _mock_response(json_data={
            "data": {
                "metric": [
                    {
                        "metric_id": 10,
                        "metric_name": "Revenue",
                        "metric_target": "1000000",
                        "metric_achieve_target": "750000",
                        "metric_unit": {"name": "Currency"},
                        "target_date": "2000000000",
                    },
                ],
            },
        })

        with _patch_client(resp):
            result = await get_my_key_results()

        assert "key_results" in result
        assert len(result["key_results"]) == 1
        assert result["key_results"][0]["name"] == "Revenue"
        assert "$" in result["key_results"][0]["progress"]

    @pytest.mark.asyncio
    async def test_get_user_key_results(self) -> None:
        """get_user_key_results should return metrics for a specific user."""
        from mcp_workboard_crunchtools.tools import get_user_key_results

        resp = _mock_response(json_data={
            "data": {
                "metric": [
                    {
                        "metric_id": 20,
                        "metric_name": "Customers",
                        "metric_target": "100",
                        "metric_achieve_target": "60",
                        "metric_unit": {"name": "Number"},
                        "target_date": "2000000000",
                    },
                ],
            },
        })

        with _patch_client(resp):
            result = await get_user_key_results(user_id=42)

        assert "key_results" in result
        assert len(result["key_results"]) == 1

    @pytest.mark.asyncio
    async def test_update_key_result(self) -> None:
        """update_key_result should put and return updated metric."""
        from mcp_workboard_crunchtools.tools import update_key_result

        metric_list_resp = _mock_response(json_data={
            "data": {
                "metric": [
                    {
                        "metric_id": 10,
                        "metric_name": "Revenue",
                        "metric_achieve_target": "50",
                    },
                ],
            },
        })
        update_resp = _mock_response(json_data={
            "data": {"metric": {"metric_id": 10, "metric_achieve_target": "75"}},
        })

        import os

        import mcp_workboard_crunchtools.client as client_mod
        import mcp_workboard_crunchtools.config as config_mod

        client_mod._client = None
        config_mod._config = None
        os.environ.setdefault("WORKBOARD_API_TOKEN", "test-mock-token")

        mock_http = AsyncMock(spec=httpx.AsyncClient)

        async def side_effect(**kwargs):  # type: ignore[no-untyped-def]
            method = kwargs.get("method", "GET")
            if method == "PUT":
                return update_resp
            return metric_list_resp

        mock_http.request = AsyncMock(side_effect=side_effect)

        with patch.object(httpx, "AsyncClient", return_value=mock_http):
            result = await update_key_result(metric_id=10, value="75")

        assert "key_result" in result


class TestClientErrorHandling:
    """Tests for HTTP error handling."""

    @pytest.mark.asyncio
    async def test_401_raises_permission_denied(self) -> None:
        """401 response should raise PermissionDeniedError."""
        from mcp_workboard_crunchtools.errors import PermissionDeniedError
        from mcp_workboard_crunchtools.tools import list_users

        resp = _mock_response(
            status_code=401,
            json_data={"message": "Unauthorized"},
        )

        with _patch_client(resp), pytest.raises(PermissionDeniedError):
            await list_users()

    @pytest.mark.asyncio
    async def test_403_raises_permission_denied(self) -> None:
        """403 response should raise PermissionDeniedError."""
        from mcp_workboard_crunchtools.errors import PermissionDeniedError
        from mcp_workboard_crunchtools.tools import list_users

        resp = _mock_response(
            status_code=403,
            json_data={"message": "Forbidden"},
        )

        with _patch_client(resp), pytest.raises(PermissionDeniedError):
            await list_users()

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit(self) -> None:
        """429 response should raise RateLimitError."""
        from mcp_workboard_crunchtools.errors import RateLimitError
        from mcp_workboard_crunchtools.tools import list_users

        resp = _mock_response(
            status_code=429,
            json_data={"message": "Rate limited", "retry_after": 60},
        )

        with _patch_client(resp), pytest.raises(RateLimitError):
            await list_users()
