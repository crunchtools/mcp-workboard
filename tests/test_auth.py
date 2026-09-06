"""Tests for OAuth 2 token management."""

import base64
import hashlib
import json
import os
import stat
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from mcp_workboard_crunchtools.auth import (
    TokenData,
    TokenStore,
    _generate_pkce,
    _parse_token_response,
)
from mcp_workboard_crunchtools.errors import (
    AuthenticationError,
    TokenExpiredError,
)

FAKE_TOKEN_URL = "https://example.com/token"


class TestTokenData:
    """Tests for the TokenData Pydantic model."""

    def test_create_with_refresh_token(self) -> None:
        td = TokenData(
            access_token=SecretStr("access"),
            refresh_token=SecretStr("refresh"),
            expires_at=1000.0,
        )
        assert td.access_token.get_secret_value() == "access"
        assert td.refresh_token is not None
        assert td.refresh_token.get_secret_value() == "refresh"
        assert td.expires_at == 1000.0

    def test_create_without_refresh_token(self) -> None:
        td = TokenData(
            access_token=SecretStr("access"),
            expires_at=1000.0,
        )
        assert td.refresh_token is None

    def test_secret_str_hides_value(self) -> None:
        td = TokenData(
            access_token=SecretStr("my-secret"),
            expires_at=1000.0,
        )
        assert "my-secret" not in repr(td)


class TestTokenStore:
    """Tests for token file persistence."""

    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        store = TokenStore(path=tmp_path / "tokens.json")
        data = TokenData(
            access_token=SecretStr("access-123"),
            refresh_token=SecretStr("refresh-456"),
            expires_at=9999999999.0,
        )
        store.save(data)
        loaded = store.load()
        assert loaded is not None
        assert loaded.access_token.get_secret_value() == "access-123"
        assert loaded.refresh_token is not None
        assert loaded.refresh_token.get_secret_value() == "refresh-456"
        assert loaded.expires_at == 9999999999.0

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        store = TokenStore(path=tmp_path / "deep" / "nested" / "tokens.json")
        data = TokenData(
            access_token=SecretStr("token"),
            expires_at=1000.0,
        )
        store.save(data)
        assert store.path.exists()

    def test_file_permissions(self, tmp_path: Path) -> None:
        store = TokenStore(path=tmp_path / "tokens.json")
        data = TokenData(access_token=SecretStr("token"), expires_at=1000.0)
        store.save(data)
        mode = store.path.stat().st_mode
        assert mode & stat.S_IRWXG == 0
        assert mode & stat.S_IRWXO == 0

    def test_load_missing_file(self, tmp_path: Path) -> None:
        store = TokenStore(path=tmp_path / "nonexistent.json")
        assert store.load() is None

    def test_load_corrupt_json(self, tmp_path: Path) -> None:
        path = tmp_path / "tokens.json"
        path.write_text("not json", encoding="utf-8")
        store = TokenStore(path=path)
        assert store.load() is None

    def test_env_var_overrides_path(self, tmp_path: Path) -> None:
        custom_path = str(tmp_path / "custom.json")
        with patch.dict(os.environ, {"WORKBOARD_TOKEN_STORE_PATH": custom_path}):
            store = TokenStore()
            assert str(store.path) == custom_path

    def test_get_access_token_cached_valid(self, tmp_path: Path) -> None:
        store = TokenStore(path=tmp_path / "tokens.json")
        data = TokenData(
            access_token=SecretStr("valid-token"),
            refresh_token=SecretStr("refresh"),
            expires_at=time.time() + 3600,
        )
        store.save(data)
        token = store.get_access_token(
            client_id="cid",
            client_secret=SecretStr("csecret"),
            token_url=FAKE_TOKEN_URL,
        )
        assert token == "valid-token"

    def test_get_access_token_no_tokens(self, tmp_path: Path) -> None:
        store = TokenStore(path=tmp_path / "nonexistent.json")
        with pytest.raises(TokenExpiredError, match="No OAuth tokens found"):
            store.get_access_token(
                client_id="cid",
                client_secret=SecretStr("csecret"),
                token_url=FAKE_TOKEN_URL,
            )

    def test_get_access_token_expired_no_refresh(self, tmp_path: Path) -> None:
        store = TokenStore(path=tmp_path / "tokens.json")
        data = TokenData(
            access_token=SecretStr("expired"),
            expires_at=time.time() - 100,
        )
        store.save(data)
        with pytest.raises(TokenExpiredError, match="no refresh token"):
            store.get_access_token(
                client_id="cid",
                client_secret=SecretStr("csecret"),
                token_url=FAKE_TOKEN_URL,
            )

    def test_get_access_token_refreshes(self, tmp_path: Path) -> None:
        store = TokenStore(path=tmp_path / "tokens.json")
        data = TokenData(
            access_token=SecretStr("old-token"),
            refresh_token=SecretStr("refresh-token"),
            expires_at=time.time() - 100,
        )
        store.save(data)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response

        with patch("mcp_workboard_crunchtools.auth.httpx.Client", return_value=mock_client):
            token = store.get_access_token(
                client_id="cid",
                client_secret=SecretStr("csecret"),
                token_url=FAKE_TOKEN_URL,
            )

        assert token == "new-token"
        reloaded = store.load()
        assert reloaded is not None
        assert reloaded.access_token.get_secret_value() == "new-token"


class TestParseTokenResponse:
    """Tests for _parse_token_response."""

    def test_valid_response(self) -> None:
        result = _parse_token_response(
            {
                "access_token": "at",
                "refresh_token": "rt",
                "expires_in": 7200,
            }
        )
        assert result.access_token.get_secret_value() == "at"
        assert result.refresh_token is not None
        assert result.refresh_token.get_secret_value() == "rt"
        assert result.expires_at > time.time()

    def test_missing_access_token(self) -> None:
        with pytest.raises(AuthenticationError, match="missing access_token"):
            _parse_token_response({"refresh_token": "rt"})

    def test_no_refresh_uses_fallback(self) -> None:
        fallback = SecretStr("fallback-rt")
        result = _parse_token_response(
            {"access_token": "at", "expires_in": 3600},
            fallback_refresh_token=fallback,
        )
        assert result.refresh_token is not None
        assert result.refresh_token.get_secret_value() == "fallback-rt"

    def test_defaults_expires_in(self) -> None:
        result = _parse_token_response({"access_token": "at"})
        assert result.expires_at > time.time()
        assert result.expires_at <= time.time() + 3601


class TestPKCE:
    """Tests for PKCE code challenge generation."""

    def test_verifier_length(self) -> None:
        verifier, _ = _generate_pkce()
        assert 43 <= len(verifier) <= 128

    def test_challenge_is_s256(self) -> None:
        verifier, challenge = _generate_pkce()
        expected = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
            .rstrip(b"=")
            .decode("ascii")
        )
        assert challenge == expected

    def test_different_each_call(self) -> None:
        v1, _ = _generate_pkce()
        v2, _ = _generate_pkce()
        assert v1 != v2


class TestConfigDualMode:
    """Tests for dual auth mode detection in Config."""

    def test_static_token_mode(self) -> None:
        from mcp_workboard_crunchtools.config import AuthMode, Config

        with patch.dict(os.environ, {"WORKBOARD_API_TOKEN": "test-jwt"}, clear=False):
            for var in ("WORKBOARD_CLIENT_ID", "WORKBOARD_CLIENT_SECRET"):
                os.environ.pop(var, None)
            config = Config()
            assert config.auth_mode == AuthMode.STATIC_TOKEN
            assert config.token == "test-jwt"

    def test_oauth_mode(self, tmp_path: Path) -> None:
        from mcp_workboard_crunchtools.config import AuthMode, Config

        tokens_path = tmp_path / "tokens.json"
        tokens_path.write_text(
            json.dumps(
                {
                    "access_token": "oauth-at",
                    "refresh_token": "oauth-rt",
                    "expires_at": time.time() + 3600,
                }
            ),
            encoding="utf-8",
        )

        env = {
            "WORKBOARD_CLIENT_ID": "test-cid",
            "WORKBOARD_CLIENT_SECRET": "test-csecret",
            "WORKBOARD_TOKEN_STORE_PATH": str(tokens_path),
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("WORKBOARD_API_TOKEN", None)
            os.environ.pop("WORKBOARD_API_TOKEN_FILE", None)
            config = Config()
            assert config.auth_mode == AuthMode.OAUTH
            assert config.token == "oauth-at"

    def test_static_token_takes_precedence(self) -> None:
        from mcp_workboard_crunchtools.config import AuthMode, Config

        env = {
            "WORKBOARD_API_TOKEN": "static-jwt",
            "WORKBOARD_CLIENT_ID": "cid",
            "WORKBOARD_CLIENT_SECRET": "csecret",
        }
        with patch.dict(os.environ, env, clear=False):
            config = Config()
            assert config.auth_mode == AuthMode.STATIC_TOKEN

    def test_no_credentials_raises(self) -> None:
        from mcp_workboard_crunchtools.config import Config
        from mcp_workboard_crunchtools.errors import ConfigurationError

        for var in (
            "WORKBOARD_API_TOKEN",
            "WORKBOARD_API_TOKEN_FILE",
            "WORKBOARD_CLIENT_ID",
            "WORKBOARD_CLIENT_SECRET",
        ):
            os.environ.pop(var, None)

        with pytest.raises(ConfigurationError, match="Authentication required"):
            Config()
