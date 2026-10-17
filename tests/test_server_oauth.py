"""Tests for server-side OAuth: pending state, the /callback route, auth tools."""

import json
import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import pytest
from starlette.requests import Request
from starlette.testclient import TestClient

import mcp_workboard_crunchtools.auth as auth_mod
from mcp_workboard_crunchtools.auth import (
    PENDING_LOGIN_TTL_SECONDS,
    PendingLogin,
    build_authorize_url,
)
from mcp_workboard_crunchtools.errors import AuthenticationError, ConfigurationError

REDIRECT_URI = "https://workboard.example.com/callback"


@pytest.fixture(autouse=True)
def fresh_pending(monkeypatch: pytest.MonkeyPatch) -> PendingLogin:
    """Give every test its own pending-login slot."""
    pending = PendingLogin()
    monkeypatch.setattr(auth_mod, "_pending", pending)
    return pending


@pytest.fixture
def oauth_env(tmp_path: Path) -> Generator[Path, None, None]:
    """Configure OAuth mode with a public redirect URI and an empty token store."""
    tokens_path = tmp_path / "tokens.json"
    env = {
        "WORKBOARD_CLIENT_ID": "test-cid",
        "WORKBOARD_CLIENT_SECRET": "test-csecret",
        "WORKBOARD_TOKEN_STORE_PATH": str(tokens_path),
        "WORKBOARD_OAUTH_REDIRECT_URI": REDIRECT_URI,
    }
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("WORKBOARD_API_TOKEN", None)
        os.environ.pop("WORKBOARD_API_TOKEN_FILE", None)
        yield tokens_path


def _request(params: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/callback",
            "query_string": urlencode(params).encode("ascii"),
            "headers": [],
        }
    )


TOKEN_JSON = {"access_token": "new-at", "refresh_token": "new-rt", "expires_in": 3600}


def _token_http(status_code: int = 200, content: bytes | None = None) -> MagicMock:
    """Mock httpx.Client used for the token exchange."""
    http = MagicMock()
    body = content if content is not None else json.dumps(TOKEN_JSON).encode()
    http.post.return_value = httpx.Response(
        status_code=status_code,
        content=body,
        headers={"content-type": "application/json"},
        request=httpx.Request("POST", auth_mod.OAUTH_TOKEN_URL),
    )
    client_cls = MagicMock()
    client_cls.return_value.__enter__.return_value = http
    return client_cls


class TestPendingLogin:
    """The one-shot CSRF state."""

    def test_issued_state_verifies_once(self, fresh_pending: PendingLogin) -> None:
        state = fresh_pending.issue()
        assert fresh_pending.in_progress
        fresh_pending.verify(state)
        assert not fresh_pending.in_progress
        with pytest.raises(AuthenticationError, match="No authorization is in progress"):
            fresh_pending.verify(state)

    def test_nothing_issued_rejects(self, fresh_pending: PendingLogin) -> None:
        with pytest.raises(AuthenticationError, match="No authorization is in progress"):
            fresh_pending.verify("anything")

    def test_mismatch_rejects_and_keeps_state(self, fresh_pending: PendingLogin) -> None:
        state = fresh_pending.issue()
        with pytest.raises(AuthenticationError, match="mismatch"):
            fresh_pending.verify("forged")
        with pytest.raises(AuthenticationError, match="mismatch"):
            fresh_pending.verify(None)
        # A forged redirect must not cancel the real one.
        fresh_pending.verify(state)

    def test_expired_state_rejects(
        self, fresh_pending: PendingLogin, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        clock = [1000.0]
        monkeypatch.setattr(auth_mod.time, "monotonic", lambda: clock[0])
        state = fresh_pending.issue()
        clock[0] += PENDING_LOGIN_TTL_SECONDS + 1
        with pytest.raises(AuthenticationError, match="expired"):
            fresh_pending.verify(state)
        assert not fresh_pending.in_progress

    def test_reissue_supersedes(self, fresh_pending: PendingLogin) -> None:
        first = fresh_pending.issue()
        second = fresh_pending.issue()
        with pytest.raises(AuthenticationError, match="mismatch"):
            fresh_pending.verify(first)
        fresh_pending.verify(second)


class TestAuthorizeUrl:
    def test_parameters(self) -> None:
        url = build_authorize_url("cid", "st", REDIRECT_URI)
        parsed = urlparse(url)
        assert url.startswith(auth_mod.OAUTH_AUTHORIZE_URL + "?")
        assert parse_qs(parsed.query) == {
            "client_id": ["cid"],
            "response_type": ["code"],
            "redirect_uri": [REDIRECT_URI],
            "scope": ["all"],
            "state": ["st"],
        }


class TestCallback:
    """The /callback route."""

    @pytest.mark.asyncio
    async def test_success_saves_tokens(self, oauth_env: Path, fresh_pending: PendingLogin) -> None:
        from mcp_workboard_crunchtools.routes import oauth_callback

        state = fresh_pending.issue()
        client_cls = _token_http()
        with patch.object(auth_mod.httpx, "Client", client_cls):
            response = await oauth_callback(
                _request({"code": "the-code", "state": state, "success": "1"})
            )

        assert response.status_code == 200
        body = bytes(response.body).decode()
        assert "authorization complete" in body
        assert "the-code" not in body
        assert "new-at" not in body

        http = client_cls.return_value.__enter__.return_value
        http.post.assert_called_once()
        assert http.post.call_args.args[0] == auth_mod.OAUTH_TOKEN_URL
        assert http.post.call_args.kwargs["data"] == {
            "client_id": "test-cid",
            "client_hash": "test-csecret",
            "code": "the-code",
            "redirect_uri": REDIRECT_URI,
            "state": state,
        }

        stored = json.loads(oauth_env.read_text(encoding="utf-8"))
        assert stored["access_token"] == "new-at"
        assert stored["refresh_token"] == "new-rt"
        assert fresh_pending.outcome is not None
        assert fresh_pending.outcome.startswith("Authorization succeeded")

    @pytest.mark.asyncio
    async def test_error_param(self, oauth_env: Path, fresh_pending: PendingLogin) -> None:
        from mcp_workboard_crunchtools.routes import oauth_callback

        state = fresh_pending.issue()
        client_cls = _token_http()
        with patch.object(auth_mod.httpx, "Client", client_cls):
            response = await oauth_callback(
                _request({"error": "<script>access_denied</script>", "state": state})
            )

        assert response.status_code == 400
        body = bytes(response.body).decode()
        assert "<script>" not in body
        assert "&lt;script&gt;access_denied" in body
        client_cls.return_value.__enter__.return_value.post.assert_not_called()
        assert not oauth_env.exists()
        assert fresh_pending.outcome is not None
        assert "denied" in fresh_pending.outcome

    @pytest.mark.asyncio
    async def test_missing_code(self, oauth_env: Path, fresh_pending: PendingLogin) -> None:
        from mcp_workboard_crunchtools.routes import oauth_callback

        state = fresh_pending.issue()
        client_cls = _token_http()
        with patch.object(auth_mod.httpx, "Client", client_cls):
            response = await oauth_callback(_request({"state": state, "success": "1"}))

        assert response.status_code == 400
        assert "no authorization code" in bytes(response.body).decode()
        client_cls.return_value.__enter__.return_value.post.assert_not_called()
        assert not oauth_env.exists()
        assert fresh_pending.outcome is not None
        assert "no authorization code" in fresh_pending.outcome

    @pytest.mark.asyncio
    async def test_state_mismatch_rejected(
        self, oauth_env: Path, fresh_pending: PendingLogin
    ) -> None:
        from mcp_workboard_crunchtools.routes import oauth_callback

        fresh_pending.issue()
        client_cls = _token_http()
        with patch.object(auth_mod.httpx, "Client", client_cls):
            response = await oauth_callback(_request({"code": "c", "state": "forged"}))

        assert response.status_code == 400
        client_cls.return_value.__enter__.return_value.post.assert_not_called()
        assert not oauth_env.exists()

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("oauth_env")
    async def test_stray_hit_does_not_overwrite_outcome(self, fresh_pending: PendingLogin) -> None:
        from mcp_workboard_crunchtools.routes import oauth_callback

        fresh_pending.record("Authorization succeeded. Tokens stored.")
        response = await oauth_callback(_request({"code": "c", "state": "x"}))
        assert response.status_code == 400
        assert fresh_pending.outcome == "Authorization succeeded. Tokens stored."

    @pytest.mark.asyncio
    async def test_exchange_failure_hides_body(
        self, oauth_env: Path, fresh_pending: PendingLogin
    ) -> None:
        from mcp_workboard_crunchtools.routes import oauth_callback

        state = fresh_pending.issue()
        with patch.object(auth_mod.httpx, "Client", _token_http(status_code=400)):
            response = await oauth_callback(_request({"code": "the-code", "state": state}))

        assert response.status_code == 400
        body = bytes(response.body).decode()
        assert "HTTP 400" in body
        assert "new-at" not in body
        assert "the-code" not in body
        assert not oauth_env.exists()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("content", "message"),
        [(b"not json", "Token exchange failed"), (b"[1, 2]", "unexpected response")],
    )
    async def test_exchange_bad_body_saves_nothing(
        self, oauth_env: Path, fresh_pending: PendingLogin, content: bytes, message: str
    ) -> None:
        from mcp_workboard_crunchtools.routes import oauth_callback

        state = fresh_pending.issue()
        with patch.object(auth_mod.httpx, "Client", _token_http(content=content)):
            response = await oauth_callback(_request({"code": "the-code", "state": state}))

        assert response.status_code == 400
        body = bytes(response.body).decode()
        assert message in body
        assert "the-code" not in body
        assert "not json" not in body
        assert not oauth_env.exists()

    @pytest.mark.asyncio
    async def test_exchange_oversized_response_rejected(
        self, oauth_env: Path, fresh_pending: PendingLogin, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from mcp_workboard_crunchtools.routes import oauth_callback

        monkeypatch.setattr(auth_mod, "MAX_RESPONSE_SIZE", 10)
        state = fresh_pending.issue()
        with patch.object(auth_mod.httpx, "Client", _token_http()):
            response = await oauth_callback(_request({"code": "the-code", "state": state}))

        assert response.status_code == 400
        assert "too large" in bytes(response.body).decode()
        assert not oauth_env.exists()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field", ["code", "state", "error"])
    async def test_overlong_params_rejected(
        self, oauth_env: Path, fresh_pending: PendingLogin, field: str
    ) -> None:
        from mcp_workboard_crunchtools.routes import oauth_callback
        from mcp_workboard_crunchtools.tools.auth import CALLBACK_PARAM_MAX_LENGTH

        state = fresh_pending.issue()
        params = {"code": "c", "state": state}
        params[field] = "x" * (CALLBACK_PARAM_MAX_LENGTH + 1)
        client_cls = _token_http()
        with patch.object(auth_mod.httpx, "Client", client_cls):
            response = await oauth_callback(_request(params))

        assert response.status_code == 400
        assert "too long" in bytes(response.body).decode()
        client_cls.return_value.__enter__.return_value.post.assert_not_called()
        # The real state is still usable: an oversized request consumes nothing.
        fresh_pending.verify(state)
        assert not oauth_env.exists()

    @pytest.mark.usefixtures("oauth_env")
    def test_route_is_registered(self) -> None:
        from mcp_workboard_crunchtools.server import mcp

        with TestClient(mcp.http_app()) as client:
            response = client.get("/callback", params={"code": "c", "state": "x"})
        assert response.status_code == 400


class TestAuthTools:
    @pytest.mark.asyncio
    @pytest.mark.usefixtures("oauth_env")
    async def test_start_without_redirect_uri(self) -> None:
        from mcp_workboard_crunchtools.tools import auth_start

        os.environ.pop("WORKBOARD_OAUTH_REDIRECT_URI")
        with pytest.raises(ConfigurationError, match="WORKBOARD_OAUTH_REDIRECT_URI"):
            await auth_start()

    @pytest.mark.asyncio
    async def test_start_in_static_mode(self) -> None:
        from mcp_workboard_crunchtools.tools import auth_start

        with (
            patch.dict(os.environ, {"WORKBOARD_API_TOKEN": "jwt"}, clear=False),
            pytest.raises(ConfigurationError, match="needs OAuth mode"),
        ):
            await auth_start()

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("oauth_env")
    async def test_start_returns_url_with_issued_state(self, fresh_pending: PendingLogin) -> None:
        from mcp_workboard_crunchtools.tools import auth_start

        text = await auth_start()
        url = next(line for line in text.splitlines() if line.startswith("https://"))
        state = parse_qs(urlparse(url).query)["state"][0]
        fresh_pending.verify(state)

    @pytest.mark.asyncio
    async def test_status_without_token(self, oauth_env: Path) -> None:
        from mcp_workboard_crunchtools.tools import auth_status

        text = await auth_status()
        assert "Auth mode: oauth" in text
        assert str(oauth_env) in text
        assert "Token present: no" in text
        assert "workboard_auth_start_tool" in text

    @pytest.mark.asyncio
    async def test_status_verifies_with_get_user(self) -> None:
        from mcp_workboard_crunchtools.tools import auth_status
        from tests.conftest import _mock_response, _patch_client

        resp = _mock_response(json_data={"data": {"user": {"email": "me@example.com"}}})
        with (
            patch.dict(os.environ, {"WORKBOARD_API_TOKEN": "jwt"}, clear=False),
            _patch_client(resp) as client_cls,
        ):
            text = await auth_status()
        call = client_cls.return_value.request.await_args
        assert call.kwargs["method"] == "GET"
        assert "verified" in text
        assert "Account: me@example.com" in text

    @pytest.mark.asyncio
    async def test_status_static_token_rejected(self) -> None:
        from mcp_workboard_crunchtools.tools import auth_status
        from tests.conftest import _mock_response, _patch_client

        resp = _mock_response(status_code=401, json_data={"message": "bad token"})
        with (
            patch.dict(os.environ, {"WORKBOARD_API_TOKEN": "jwt"}, clear=False),
            _patch_client(resp),
        ):
            text = await auth_status()
        assert "Auth mode: static_token" in text
        assert "REJECTED" in text
        assert "workboard_auth_start_tool" not in text

    @pytest.mark.asyncio
    async def test_status_oauth_token_rejected(self, oauth_env: Path) -> None:
        from mcp_workboard_crunchtools.tools import auth_status
        from tests.conftest import _mock_response

        oauth_env.write_text(
            json.dumps({"access_token": "at", "refresh_token": "rt", "expires_at": 9e12}),
            encoding="utf-8",
        )
        resp = _mock_response(status_code=401, json_data={"message": "bad token"})
        mock_http = MagicMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(return_value=resp)
        with patch.object(httpx, "AsyncClient", return_value=mock_http):
            text = await auth_status()
        assert "Token present: yes" in text
        assert "REJECTED" in text
        assert "workboard_auth_start_tool" in text

    @pytest.mark.asyncio
    async def test_result_before_any_redirect(self) -> None:
        from mcp_workboard_crunchtools.tools import auth_result

        assert "No authorization redirect" in await auth_result()
