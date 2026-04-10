"""Shared test fixtures for mcp-workboard tests."""

import os
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _reset_client_singleton() -> Generator[None, None, None]:
    """Reset the global client and config singletons between tests."""
    import mcp_workboard_crunchtools.client as client_mod
    import mcp_workboard_crunchtools.config as config_mod

    client_mod._client = None
    config_mod._config = None
    yield
    client_mod._client = None
    config_mod._config = None


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


def _patch_client(mock_response: httpx.Response):
    """Patch the httpx AsyncClient to return a mock response.

    Sets WORKBOARD_API_TOKEN so config initializes, then mocks the HTTP layer.
    """
    import mcp_workboard_crunchtools.client as client_mod
    import mcp_workboard_crunchtools.config as config_mod

    client_mod._client = None
    config_mod._config = None

    os.environ.setdefault("WORKBOARD_API_TOKEN", "test-mock-token")

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.request = AsyncMock(return_value=mock_response)

    return patch.object(
        httpx,
        "AsyncClient",
        return_value=mock_http,
    )
