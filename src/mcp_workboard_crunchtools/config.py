"""Secure configuration handling."""

import logging
import os

from pydantic import SecretStr

from .errors import ConfigurationError

logger = logging.getLogger(__name__)


class Config:
    """Secure configuration handling.

    The API token is stored as a SecretStr and should only be accessed
    via the token property when actually needed for API calls.
    """

    def __init__(self) -> None:
        """Initialize configuration from environment variables.

        Raises:
            ConfigurationError: If required environment variables are missing.
        """
        token = os.environ.get("WORKBOARD_API_TOKEN")
        if not token:
            raise ConfigurationError(
                "WORKBOARD_API_TOKEN environment variable required. "
                "Generate a JWT token from your WorkBoard admin settings."
            )

        self._token = SecretStr(token)
        logger.info("Configuration loaded successfully")

    @property
    def token(self) -> str:
        """Get token value for API calls.

        Use sparingly - only when making actual API calls.
        """
        return self._token.get_secret_value()

    @property
    def api_base_url(self) -> str:
        """Hardcoded WorkBoard API base URL.

        This is intentionally not configurable to prevent SSRF attacks.
        """
        return "https://www.myworkboard.com/wb/apis"

    def __repr__(self) -> str:
        """Safe repr that never exposes the token."""
        return "Config(token=***)"

    def __str__(self) -> str:
        """Safe str that never exposes the token."""
        return "Config(token=***)"



_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance.

    This function lazily initializes the configuration on first call.
    Subsequent calls return the same instance.

    Returns:
        The global Config instance.

    Raises:
        ConfigurationError: If configuration is invalid.
    """
    global _config
    if _config is None:
        _config = Config()
    return _config
