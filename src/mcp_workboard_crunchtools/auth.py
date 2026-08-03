"""OAuth 2 token management and authorization code flow."""

import base64
import hashlib
import json
import logging
import os
import secrets
import stat
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from pydantic import BaseModel, SecretStr

from .errors import AuthenticationError, TokenExpiredError

logger = logging.getLogger(__name__)

REFRESH_MARGIN_SECONDS = 60
DEFAULT_TOKEN_STORE_PATH = Path.home() / ".config" / "mcp-workboard" / "tokens.json"
DEFAULT_CALLBACK_PORT = 8963

OAUTH_AUTHORIZE_URL = "https://www.myworkboard.com/wb/oauth/authorize"
OAUTH_TOKEN_URL = "https://www.myworkboard.com/wb/oauth/token"


class TokenData(BaseModel):
    """Serializable OAuth token set."""

    access_token: SecretStr
    refresh_token: SecretStr | None = None
    expires_at: float


class TokenStore:
    """Read/write OAuth tokens from a local JSON file."""

    def __init__(self, path: Path | None = None) -> None:
        env_path = os.environ.get("WORKBOARD_TOKEN_STORE_PATH")
        if env_path:
            self._path = Path(env_path)
        elif path is not None:
            self._path = path
        else:
            self._path = DEFAULT_TOKEN_STORE_PATH
        self._cached: TokenData | None = None

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> TokenData | None:
        if not self._path.exists():
            return None
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._cached = TokenData(
                access_token=SecretStr(raw["access_token"]),
                refresh_token=SecretStr(raw["refresh_token"]) if raw.get("refresh_token") else None,
                expires_at=float(raw["expires_at"]),
            )
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
            logger.warning("Failed to load tokens from %s: %s", self._path, e)
            return None
        else:
            return self._cached

    def save(self, data: TokenData) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "access_token": data.access_token.get_secret_value(),
                "refresh_token": (
                    data.refresh_token.get_secret_value() if data.refresh_token else None
                ),
                "expires_at": data.expires_at,
            },
            indent=2,
        )
        fd = os.open(
            str(self._path),
            os.O_CREAT | os.O_WRONLY | os.O_TRUNC,
            stat.S_IRUSR | stat.S_IWUSR,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
        except Exception:
            os.close(fd)
            raise
        self._cached = data
        logger.info("Tokens saved to %s", self._path)

    def get_access_token(
        self,
        client_id: str,
        client_secret: SecretStr,
        token_url: str,
    ) -> str:
        if self._cached is None:
            self._cached = self.load()
        if self._cached is None:
            raise TokenExpiredError(
                "No OAuth tokens found. Run `mcp-workboard-crunchtools login` first."
            )

        if time.time() < self._cached.expires_at - REFRESH_MARGIN_SECONDS:
            return self._cached.access_token.get_secret_value()

        if self._cached.refresh_token is None:
            raise TokenExpiredError(
                "Access token expired and no refresh token available. "
                "Run `mcp-workboard-crunchtools login` again."
            )

        logger.info("Access token expired, refreshing...")
        try:
            with httpx.Client(timeout=30.0, verify=True) as http:
                response = http.post(
                    token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self._cached.refresh_token.get_secret_value(),
                        "client_id": client_id,
                        "client_hash": client_secret.get_secret_value(),
                    },
                )
                response.raise_for_status()
                token_response = response.json()
        except (httpx.HTTPError, ValueError) as e:
            raise TokenExpiredError(
                f"Token refresh failed: {e}. Run `mcp-workboard-crunchtools login` again."
            ) from e

        new_data = _parse_token_response(token_response, self._cached.refresh_token)
        self.save(new_data)
        return new_data.access_token.get_secret_value()


def _parse_token_response(
    response: dict[str, Any],
    fallback_refresh_token: SecretStr | None = None,
) -> TokenData:
    access_token = response.get("access_token")
    if not access_token:
        raise AuthenticationError("Token response missing access_token")

    refresh_token = response.get("refresh_token")
    expires_in = int(response.get("expires_in", 3600))

    return TokenData(
        access_token=SecretStr(access_token),
        refresh_token=(SecretStr(refresh_token) if refresh_token else fallback_refresh_token),
        expires_at=time.time() + expires_in,
    )


def _generate_pkce() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


class _CallbackHandler(BaseHTTPRequestHandler):
    """Captures the OAuth callback and stores code + state on the server instance."""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        server: _CallbackServer = self.server  # type: ignore[assignment]
        code_values = params.get("code", [])
        state_values = params.get("state", [])
        error_values = params.get("error", [])
        server.callback_code = code_values[0] if code_values else None
        server.callback_state = state_values[0] if state_values else None
        server.callback_error = error_values[0] if error_values else None

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        body = (
            "<html><body><h2>Login successful!</h2>"
            "<p>You can close this tab and return to the terminal.</p>"
            "</body></html>"
        )
        self.wfile.write(body.encode("utf-8"))

        Thread(target=server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args: Any) -> None:
        pass


class _CallbackServer(HTTPServer):
    """HTTPServer subclass with storage for the OAuth callback parameters."""

    callback_code: str | None = None
    callback_state: str | None = None
    callback_error: str | None = None


def run_login_flow(
    client_id: str,
    client_secret: SecretStr,
    token_store: TokenStore,
    callback_port: int = DEFAULT_CALLBACK_PORT,
) -> None:
    """Execute the full OAuth 2 authorization code flow."""
    redirect_uri = f"http://localhost:{callback_port}/callback"

    state = secrets.token_urlsafe(32)

    params = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "all",
            "state": state,
        }
    )
    auth_url = f"{OAUTH_AUTHORIZE_URL}?{params}"

    server = _CallbackServer(("127.0.0.1", callback_port), _CallbackHandler)

    print("Opening browser for WorkBoard login...")
    print(f"If the browser does not open, visit:\n  {auth_url}")
    webbrowser.open(auth_url)

    print("Waiting for callback...")
    server.serve_forever()

    if server.callback_error:
        raise AuthenticationError(f"WorkBoard denied authorization: {server.callback_error}")

    if server.callback_code is None:
        raise AuthenticationError("No authorization code received in callback")

    if server.callback_state != state:
        raise AuthenticationError("State parameter mismatch — possible CSRF attack")

    print("Exchanging authorization code for tokens...")
    try:
        with httpx.Client(timeout=30.0, verify=True) as http:
            response = http.post(
                OAUTH_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_hash": client_secret.get_secret_value(),
                    "code": server.callback_code,
                    "redirect_uri": redirect_uri,
                    "state": state,
                },
            )
            response.raise_for_status()
            token_response = response.json()
    except httpx.HTTPStatusError as e:
        raise AuthenticationError(
            f"Token exchange failed (HTTP {e.response.status_code}): {e.response.text}"
        ) from e
    except (httpx.HTTPError, ValueError) as e:
        raise AuthenticationError(f"Token exchange failed: {e}") from e

    token_data = _parse_token_response(token_response)
    token_store.save(token_data)
    print(f"Login successful! Tokens saved to {token_store.path}")
