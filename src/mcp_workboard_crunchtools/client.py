"""WorkBoard API client with security hardening."""

import logging
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
                headers={
                    "Authorization": f"Bearer {self._config.token}",
                    "Content-Type": "application/json",
                },
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
    ) -> dict[str, Any]:
        """Make an API request with error handling.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: API path (e.g., /user)
            params: Query parameters
            json_data: JSON body data

        Returns:
            API response data

        Raises:
            WorkBoardApiError: On API errors
            RateLimitError: On rate limiting
            PermissionDeniedError: On authorization failures
        """
        client = await self._get_client()

        logger.debug("API request: %s %s", method, path)

        try:
            response = await client.request(
                method=method,
                url=path,
                params=params,
                json=json_data,
            )
        except httpx.TimeoutException as e:
            raise WorkBoardApiError(0, f"Request timeout: {e}") from e
        except httpx.RequestError as e:
            raise WorkBoardApiError(0, f"Request failed: {e}") from e

        body = response.content
        if len(body) > MAX_RESPONSE_SIZE:
            raise WorkBoardApiError(0, "Response too large")

        try:
            parsed = response.json()
        except ValueError as e:
            raise WorkBoardApiError(
                response.status_code, f"Invalid JSON response: {e}"
            ) from e

        if not response.is_success:
            self._handle_error_response(response.status_code, parsed)

        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}

    def _handle_error_response(
        self, status_code: int, error_body: dict[str, Any]
    ) -> None:
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
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GET request."""
        return await self._request("GET", path, params=params)

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
