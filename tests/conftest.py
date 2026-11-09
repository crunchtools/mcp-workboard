"""Shared test fixtures for mcp-workboard tests."""

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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


def dispatch_on_kwargs(mock_http: AsyncMock, reply: Any) -> None:
    """Make a client stand-in answer from the kwargs the caller passed.

    The client streams now, so `send` receives a built request rather than the
    `method=`/`url=` keywords a dispatching test wants to branch on. This
    records those keywords in `build_request` and hands them to `reply`, which
    keeps such a test written in the terms it cares about.
    """
    asked: list[dict[str, Any]] = []
    builder = httpx.Client()

    def build(**kwargs: Any) -> httpx.Request:
        asked.append(kwargs)
        return builder.build_request(**kwargs)

    async def send(_request: httpx.Request, **_: Any) -> httpx.Response:
        return await reply(**asked[-1])

    mock_http.build_request = MagicMock(side_effect=build)
    mock_http.send = AsyncMock(side_effect=send)


def _patch_client(mock_response: httpx.Response):
    """Patch the httpx AsyncClient to return a mock response.

    Sets WORKBOARD_API_TOKEN so config initializes, then mocks the HTTP layer.
    """
    import mcp_workboard_crunchtools.client as client_mod
    import mcp_workboard_crunchtools.config as config_mod

    client_mod._client = None
    config_mod._config = None

    os.environ.setdefault("WORKBOARD_API_TOKEN", "test-mock-token")

    # The client streams now: `build_request` then `send(..., stream=True)`. A
    # real client builds the request, so a test that inspects what was asked
    # still sees it; `send` is what each test scripts.
    #
    # What a mock of the client cannot see is the client's own behaviour -- the
    # User-Agent it adds and the bounded read it performs. Those are tested in
    # `test_http_contract.py` over a `MockTransport` (constitution v1.36.0,
    # Layer 3).
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.build_request = MagicMock(side_effect=httpx.Client().build_request)
    mock_http.send = AsyncMock(return_value=mock_response)

    return patch.object(
        httpx,
        "AsyncClient",
        return_value=mock_http,
    )
