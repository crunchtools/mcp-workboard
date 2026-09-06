"""Safe error types that can be shown to users.

This module defines exception classes that are safe to expose to MCP clients.
Internal errors should be caught and converted to UserError before propagating.
"""

import os


class UserError(Exception):
    """Base class for safe errors that can be shown to users.

    All error messages in UserError subclasses must be carefully crafted
    to avoid leaking sensitive information like API tokens or internal paths.
    """

    pass


class ConfigurationError(UserError):
    """Error in server configuration."""

    pass


class InvalidUserIdError(UserError):
    """Invalid user ID format."""

    def __init__(self) -> None:
        super().__init__("Invalid user_id format. Expected positive integer.")


class InvalidObjectiveIdError(UserError):
    """Invalid objective ID format."""

    def __init__(self) -> None:
        super().__init__("Invalid objective_id format. Expected positive integer.")


class InvalidMetricIdError(UserError):
    """Invalid metric ID format."""

    def __init__(self) -> None:
        super().__init__("Invalid metric_id format. Expected positive integer.")


class InvalidWorkstreamIdError(UserError):
    """Invalid workstream ID format."""

    def __init__(self) -> None:
        super().__init__("Invalid workstream_id format. Expected positive integer.")


class InvalidActivityIdError(UserError):
    """Invalid activity ID format."""

    def __init__(self) -> None:
        super().__init__("Invalid activity_id format. Expected positive integer.")


SAFE_ID_MAX_LENGTH = 20


class NotFoundError(UserError):
    """Resource not found or not accessible."""

    def __init__(self, resource: str, identifier: str) -> None:
        safe_id = (
            identifier[:SAFE_ID_MAX_LENGTH] + "..."
            if len(identifier) > SAFE_ID_MAX_LENGTH
            else identifier
        )
        super().__init__(f"{resource} not found or not accessible: {safe_id}")


class PermissionDeniedError(UserError):
    """Permission denied for the requested operation."""

    def __init__(self, required_scope: str) -> None:
        super().__init__(f"Permission denied. Required scope: {required_scope}")


class RateLimitError(UserError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int | None = None) -> None:
        msg = "Rate limit exceeded."
        if retry_after:
            msg += f" Retry after {retry_after} seconds."
        super().__init__(msg)


class WorkBoardApiError(UserError):
    """Error from WorkBoard API.

    The message is sanitized to remove any potential token references.
    """

    def __init__(self, code: int, message: str) -> None:
        safe_message = message
        for var in ("WORKBOARD_API_TOKEN", "WORKBOARD_CLIENT_SECRET"):
            secret = os.environ.get(var, "")
            if secret:
                safe_message = safe_message.replace(secret, "***")
        super().__init__(f"WorkBoard API error {code}: {safe_message}")


class ValidationError(UserError):
    """Input validation error."""

    pass


class AuthenticationError(UserError):
    """OAuth authentication flow failed."""

    pass


class TokenExpiredError(UserError):
    """OAuth tokens expired and refresh failed."""

    pass
