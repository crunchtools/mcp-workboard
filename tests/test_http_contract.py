"""The outbound HTTP contract (constitution v1.36.0, MCP Server profile Layer 3).

A real `httpx.AsyncClient` over a `MockTransport`: the agent string is a header
the client adds and the ceiling is enforced while the client reads, so the
`_patch_client` mock -- which replaces `send` -- cannot see either.
"""

import os
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import contextmanager
from importlib.metadata import version
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from mcp_workboard_crunchtools import client as client_mod
from mcp_workboard_crunchtools.errors import WorkBoardApiError

Handler = Callable[[httpx.Request], httpx.Response]


async def _chunks(chunk: bytes, times: int) -> AsyncIterator[bytes]:
    """A chunked body, which carries no content-length -- what a header check misses."""
    for _ in range(times):
        yield chunk


@contextmanager
def _serving(handler: Handler) -> Iterator[None]:
    """Let the client build itself, on a mock transport."""
    import mcp_workboard_crunchtools.config as config_mod

    real = httpx.AsyncClient

    def factory(**kwargs: Any) -> httpx.AsyncClient:
        kwargs.pop("transport", None)
        return real(transport=httpx.MockTransport(handler), **kwargs)

    with patch.dict(os.environ, {"WORKBOARD_API_TOKEN": "test-mock-token"}, clear=True):
        config_mod._config = None
        client_mod._client = None
        with patch.object(httpx, "AsyncClient", factory):
            yield
        config_mod._config = None
        client_mod._client = None


class TestUserAgent:
    """A request says what it is, and the version cannot drift from the release."""

    @pytest.mark.asyncio
    async def test_outgoing_request_names_the_product_and_version(self) -> None:
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.headers["User-Agent"])
            return httpx.Response(200, json={"data": {}})

        with _serving(handler):
            await client_mod.get_client()._request("GET", "/user")

        expected = (
            f"mcp-workboard-crunchtools/{version('mcp-workboard-crunchtools')} "
            "(+https://github.com/crunchtools/mcp-workboard)"
        )
        assert seen == [expected]
        assert "python-httpx" not in seen[0]


class TestResponseCeiling:
    """The cap compared `len(response.content)` after reading the whole body."""

    @pytest.mark.asyncio
    async def test_chunked_body_over_the_cap_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(client_mod, "MAX_RESPONSE_SIZE", 4096)

        def handler(_request: httpx.Request) -> httpx.Response:
            response = httpx.Response(
                200, headers={"content-type": "application/json"}, content=_chunks(b"x" * 1024, 16)
            )
            assert "content-length" not in response.headers
            return response

        with _serving(handler), pytest.raises(WorkBoardApiError) as caught:
            await client_mod.get_client()._request("GET", "/goal")

        assert "over the 4096 byte limit" in str(caught.value)

    @pytest.mark.asyncio
    async def test_a_single_oversized_chunk_is_refused_before_it_is_copied(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(client_mod, "MAX_RESPONSE_SIZE", 1024)

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, headers={"content-type": "application/json"}, content=_chunks(b"x" * 8192, 1)
            )

        with _serving(handler), pytest.raises(WorkBoardApiError) as caught:
            await client_mod.get_client()._request("GET", "/goal")

        assert "over the 1024 byte limit" in str(caught.value)

    @pytest.mark.asyncio
    async def test_a_declared_length_over_the_cap_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(client_mod, "MAX_RESPONSE_SIZE", 64)

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, headers={"content-type": "application/json"}, content=b"x" * 128
            )

        with _serving(handler), pytest.raises(WorkBoardApiError) as caught:
            await client_mod.get_client()._request("GET", "/goal")

        assert "over the 64 byte limit" in str(caught.value)


class TestErrorNamesTheSite:
    """RT #1596: the message has to say which site answered, and with what."""

    @pytest.mark.asyncio
    async def test_a_non_json_body_is_quoted_with_the_request(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, headers={"content-type": "text/html"}, text="<title>Sign in</title>"
            )

        with _serving(handler), pytest.raises(WorkBoardApiError) as caught:
            await client_mod.get_client()._request("GET", "/user")

        message = str(caught.value)
        assert "Sign in" in message
        assert "text/html" in message
        assert "/user" in message

    @pytest.mark.asyncio
    async def test_a_transport_failure_names_the_request(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("timed out")

        with _serving(handler), pytest.raises(WorkBoardApiError) as caught:
            await client_mod.get_client()._request("GET", "/user")

        message = str(caught.value)
        assert "Request timeout" in message
        assert "GET /user" in message

    @pytest.mark.asyncio
    async def test_workboards_own_message_is_still_used(self) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"message": "Invalid goal id"})

        with _serving(handler), pytest.raises(WorkBoardApiError) as caught:
            await client_mod.get_client()._request("GET", "/goal/0")

        assert "Invalid goal id" in str(caught.value)
