"""Secure configuration handling with dual auth mode support."""

from __future__ import annotations

import enum
import logging
import os
from typing import TYPE_CHECKING

from pydantic import SecretStr

from .errors import ConfigurationError

if TYPE_CHECKING:
    from .auth import TokenStore

logger = logging.getLogger(__name__)


class AuthMode(enum.Enum):
    """Authentication mode."""

    STATIC_TOKEN = "static_token"
    OAUTH = "oauth"


class Config:
    """Secure configuration handling.

    Supports two auth modes:
    - Static JWT token via WORKBOARD_API_TOKEN or WORKBOARD_API_TOKEN_FILE
    - OAuth 2 via WORKBOARD_CLIENT_ID + WORKBOARD_CLIENT_SECRET with cached tokens
    """

    def __init__(self) -> None:
        """Initialize configuration from environment variables.

        Raises:
            ConfigurationError: If required environment variables are missing.
        """
        token = self._load_static_token()
        if token:
            self._auth_mode = AuthMode.STATIC_TOKEN
            self._static_token = SecretStr(token)
            self._client_id: str | None = None
            self._client_secret: SecretStr | None = None
            self._token_store: TokenStore | None = None
            logger.info("Configuration loaded: static token mode")
            return

        client_id = os.environ.get("WORKBOARD_CLIENT_ID")
        client_secret = os.environ.get("WORKBOARD_CLIENT_SECRET")
        if client_id and client_secret:
            from .auth import TokenStore

            self._auth_mode = AuthMode.OAUTH
            self._static_token = SecretStr("")
            self._client_id = client_id
            self._client_secret = SecretStr(client_secret)
            self._token_store = TokenStore()
            logger.info("Configuration loaded: OAuth mode")
            return

        raise ConfigurationError(
            "Authentication required. Choose one:\n"
            "  Static token: set WORKBOARD_API_TOKEN or WORKBOARD_API_TOKEN_FILE\n"
            "  OAuth 2: set WORKBOARD_CLIENT_ID + WORKBOARD_CLIENT_SECRET, "
            "then run `mcp-workboard-crunchtools login`"
        )

    @staticmethod
    def _load_static_token() -> str | None:
        token_file = os.environ.get("WORKBOARD_API_TOKEN_FILE")
        if token_file:
            try:
                with open(token_file) as f:
                    return f.read().strip()
            except OSError as e:
                raise ConfigurationError(f"Failed to read token from {token_file}: {e}") from e

        return os.environ.get("WORKBOARD_API_TOKEN")

    @property
    def auth_mode(self) -> AuthMode:
        return self._auth_mode

    @property
    def token(self) -> str:
        """Get the current bearer token for API calls.

        In static mode, returns the JWT token.
        In OAuth mode, returns the access token (auto-refreshing if expired).
        """
        if self._auth_mode == AuthMode.STATIC_TOKEN:
            return self._static_token.get_secret_value()

        assert self._token_store is not None
        assert self._client_id is not None
        assert self._client_secret is not None
        from .auth import OAUTH_TOKEN_URL

        return self._token_store.get_access_token(
            client_id=self._client_id,
            client_secret=self._client_secret,
            token_url=OAUTH_TOKEN_URL,
        )

    @property
    def api_base_url(self) -> str:
        """Hardcoded WorkBoard API base URL.

        This is intentionally not configurable to prevent SSRF attacks.
        """
        return "https://www.myworkboard.com/wb/apis"

    def __repr__(self) -> str:
        return f"Config(mode={self._auth_mode.value}, token=***)"

    def __str__(self) -> str:
        return f"Config(mode={self._auth_mode.value}, token=***)"


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
