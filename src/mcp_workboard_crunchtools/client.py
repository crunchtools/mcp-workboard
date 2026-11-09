"""WorkBoard API client with security hardening."""

import json
import logging
from importlib.metadata import version
from typing import Any

import httpx

from .config import get_config
from .errors import (
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    WorkBoardApiError,
)

logger = logging.getLogger(__name__)

MAX_RESPONSE_SIZE = 10 * 1024 * 1024
REQUEST_TIMEOUT = 30.0
BODY_SNIPPET_CHARS = 200
ELLIPSIS = "..."

# Identify this client by name. httpx otherwise sends `python-httpx/<version>`,
# which bot protection answers with an HTML challenge page instead of the API --
# the failure that cost an afternoon on mcp-wordpress (RT #1596). The version
# comes from installed package metadata so it cannot drift from pyproject.toml.
USER_AGENT = (
    f"mcp-workboard-crunchtools/{version('mcp-workboard-crunchtools')} "
    "(+https://github.com/crunchtools/mcp-workboard)"
)


def _body_snippet(body: bytes) -> str:
    """A short, single-line excerpt of a response body, for an error message."""
    prefix = body[: BODY_SNIPPET_CHARS * 4]
    collapsed = " ".join(prefix.decode("utf-8", errors="replace").split())
    if not collapsed:
        return "<empty body>"
    if len(collapsed) > BODY_SNIPPET_CHARS or len(body) > len(prefix):
        return collapsed[: BODY_SNIPPET_CHARS - len(ELLIPSIS)] + ELLIPSIS
    return collapsed


def _where(response: httpx.Response) -> str:
    """Which request a response answered, for an error message."""
    return (
        f"{response.request.method} {response.request.url} "
        f"(HTTP {response.status_code}, {response.headers.get('content-type', 'no content-type')})"
    )


async def read_capped(response: httpx.Response, oversize: str) -> bytes:
    """Read the body, aborting as soon as it would pass MAX_RESPONSE_SIZE.

    Shared with `auth.py`, whose token exchanges had the same post-hoc check.
    `oversize` is the message to raise, because the token paths deliberately
    keep their errors to a fixed vocabulary rather than quoting a body.

    One buffer, measured before the copy: `aiter_bytes()` promises nothing about
    chunk size -- one chunk can be the whole body -- so appending first would
    copy in exactly the response being refused. Checking `len(response.content)`
    afterwards, which is what this replaces, had already spent the memory the
    limit exists to protect.
    """
    declared = response.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_RESPONSE_SIZE:
        raise WorkBoardApiError(response.status_code, oversize)
    body = bytearray()
    async for chunk in response.aiter_bytes():
        if len(body) + len(chunk) > MAX_RESPONSE_SIZE:
            raise WorkBoardApiError(response.status_code, oversize)
        body += chunk
    return bytes(body)


class WorkBoardClient:
    """Async HTTP client for WorkBoard API.

    Security features:
    - Hardcoded base URL (prevents SSRF)
    - Token passed via auth header (not URL)
    - TLS certificate validation (httpx default)
    - Request timeout enforcement
    - Response size limits
    """

    def __init__(self) -> None:
        """Initialize the WorkBoard client."""
        self._config = get_config()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._config.api_base_url,
                headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
                timeout=httpx.Timeout(REQUEST_TIMEOUT),
                verify=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Make an API request with error handling.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: API path (e.g., /user)
            params: Query parameters
            json_data: JSON body data
            timeout: Seconds, overriding REQUEST_TIMEOUT for a known-slow call

        Returns:
            API response data

        Raises:
            WorkBoardApiError: On API errors
            RateLimitError: On rate limiting
            PermissionDeniedError: On authorization failures
        """
        client = await self._get_client()
        auth_headers = {"Authorization": f"Bearer {self._config.token}"}

        logger.debug("API request: %s %s", method, path)

        try:
            request = client.build_request(
                method=method,
                url=path,
                params=params,
                json=json_data,
                headers=auth_headers,
                timeout=httpx.USE_CLIENT_DEFAULT if timeout is None else timeout,
            )
            response = await client.send(request, stream=True)
            try:
                body = await read_capped(
                    response, f"Response over the {MAX_RESPONSE_SIZE} byte limit"
                )
            finally:
                await response.aclose()
        except httpx.TimeoutException as e:
            raise WorkBoardApiError(0, f"Request timeout: {method} {path}: {e}") from e
        except httpx.RequestError as e:
            raise WorkBoardApiError(0, f"Request failed: {method} {path}: {e}") from e

        try:
            parsed = json.loads(body)
        except ValueError as e:
            raise WorkBoardApiError(
                response.status_code,
                f"{_where(response)} is not JSON ({e}): {_body_snippet(body)}",
            ) from e

        if not response.is_success:
            self._handle_error_response(response.status_code, parsed)

        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}

    def _handle_error_response(self, status_code: int, error_body: dict[str, Any]) -> None:
        """Handle error responses from the API."""
        error_msg = error_body.get("message", "Unknown error")
        if isinstance(error_msg, dict):
            error_msg = str(error_msg)

        match status_code:
            case 401:
                raise PermissionDeniedError("Valid API token")
            case 403:
                raise PermissionDeniedError("Required permission scope")
            case 404:
                raise NotFoundError("Resource", str(error_msg))
            case 429:
                retry_after = error_body.get("retry_after")
                raise RateLimitError(retry_after)
            case _:
                raise WorkBoardApiError(status_code, str(error_msg))

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Make a GET request."""
        return await self._request("GET", path, params=params, timeout=timeout)

    async def post(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request."""
        return await self._request("POST", path, params=params, json_data=json_data)

    async def put(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a PUT request."""
        return await self._request("PUT", path, json_data=json_data)

    async def patch(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a PATCH request."""
        return await self._request("PATCH", path, json_data=json_data)

    async def delete(self, path: str) -> dict[str, Any]:
        """Make a DELETE request."""
        return await self._request("DELETE", path)


_client: WorkBoardClient | None = None


def get_client() -> WorkBoardClient:
    """Get or create the global WorkBoard client singleton."""
    global _client
    if _client is None:
        _client = WorkBoardClient()
    return _client
