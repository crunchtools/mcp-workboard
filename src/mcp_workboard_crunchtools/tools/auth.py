"""Authorization status and browser-based login, exposed as MCP tools.

The point of these is that re-authorizing a containerized server is a tool
call rather than a runbook. An agent asks whether the server is authorized,
opens the URL it hands back, and the user approves in a browser. WorkBoard
redirects to the server's own ``/callback`` route, which finishes the
exchange -- nothing is copied or pasted, and no shell is involved.
"""

from __future__ import annotations

import html
import logging
from typing import TYPE_CHECKING, Any, NamedTuple

from starlette.concurrency import run_in_threadpool

from ..auth import REDIRECT_URI_VAR, build_authorize_url, complete_login, get_pending_login
from ..client import get_client
from ..config import AuthMode, get_config
from ..errors import AuthenticationError, ConfigurationError, UserError

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

# Upper bound on each value the callback reads from the query string. Real
# codes, states and error values are far shorter; anything longer is refused
# before it is used. The query string as a whole is already capped by the HTTP
# server's request-line limit, and parameters the callback does not read are
# never touched.
CALLBACK_PARAM_MAX_LENGTH = 512
FAILED_HEADING = "Authorization failed"


class CallbackOutcome(NamedTuple):
    """What the ``/callback`` page tells the human, and its HTTP status."""

    heading: str
    detail: str
    status_code: int

    def page(self) -> str:
        """Render the minimal page a human sees after being redirected back.

        Both strings are escaped: ``detail`` can carry WorkBoard's ``error``
        query parameter, which anyone can put in a link to this route.
        """
        safe_heading = html.escape(self.heading)
        safe_detail = html.escape(self.detail)
        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{safe_heading}</title></head>"
            "<body style='font-family:system-ui;max-width:34rem;margin:4rem auto'>"
            f"<h2>{safe_heading}</h2><p>{safe_detail}</p></body></html>"
        )


def _user_email(payload: dict[str, Any]) -> str:
    """Pull the caller's email out of a ``GET /user`` response.

    WorkBoard wraps the user in ``data.user``; anything else yields an empty
    string rather than an error, since the call succeeding is what matters.
    """
    envelope = payload.get("data")
    user = envelope.get("user") if isinstance(envelope, dict) else None
    if not isinstance(user, dict):
        return ""
    return str(user.get("email") or "")


async def auth_status() -> str:
    """Report whether the server holds a usable WorkBoard credential.

    Answers the only question worth asking before doing work: can this
    server talk to WorkBoard right now, and if not, what is missing?
    """
    config = get_config()
    lines = [f"Auth mode: {config.auth_mode.value}"]

    if config.auth_mode is AuthMode.STATIC_TOKEN:
        lines.append("Token store: not used (static token supplied by configuration)")
    else:
        token_store = config.token_store
        if token_store is None:
            raise ConfigurationError("OAuth mode is not fully configured")
        lines.append(f"Token store: {token_store.path}")
        if token_store.load() is None:
            lines.append("Token present: no")
            lines.append("Status: NOT AUTHORIZED -- no token stored")
            lines.append("Run the workboard_auth_start_tool to begin browser authorization.")
            return "\n".join(lines)
        lines.append("Token present: yes")

    try:
        payload = await get_client().get("/user")
    except UserError as exc:
        lines.append(f"Status: credential REJECTED by WorkBoard -- {exc}")
        if config.auth_mode is AuthMode.OAUTH:
            lines.append("Run the workboard_auth_start_tool to authorize again.")
        return "\n".join(lines)

    lines.append("Status: authorized and verified against WorkBoard")
    lines.append(f"Account: {_user_email(payload) or 'unknown'}")
    return "\n".join(lines)


async def auth_start() -> str:
    """Begin browser authorization and return the URL to open.

    The caller opens the returned URL; the user approves there. WorkBoard then
    redirects to this server's ``/callback`` route, which completes the
    exchange and stores the tokens. Poll ``workboard_auth_status_tool``
    afterwards to confirm.

    Raises:
        ConfigurationError: If the server is not in OAuth mode, or has no
            public redirect URI configured.
    """
    config = get_config()

    if config.auth_mode is not AuthMode.OAUTH or config.client_id is None:
        raise ConfigurationError(
            f"Browser authorization needs OAuth mode, but this server is in "
            f"{config.auth_mode.value} mode. Set WORKBOARD_CLIENT_ID and "
            "WORKBOARD_CLIENT_SECRET, and unset WORKBOARD_API_TOKEN."
        )

    redirect_uri = config.oauth_redirect_uri
    if not redirect_uri:
        raise ConfigurationError(
            f"{REDIRECT_URI_VAR} is not set. Browser authorization needs a URL "
            "WorkBoard can redirect to that reaches this server's /callback "
            "route -- for a container behind a reverse proxy, that is the "
            "public https URL. It must match the redirect URI registered for "
            "the WorkBoard app."
        )

    url = build_authorize_url(config.client_id, get_pending_login().issue(), redirect_uri)
    return (
        "Open this URL in a browser and approve the application:\n\n"
        f"{url}\n\n"
        f"WorkBoard will redirect to {redirect_uri}, which this server handles "
        "directly. Nothing needs to be copied back.\n"
        "Then call workboard_auth_status_tool to confirm the token was stored.\n"
        "The authorization expires in 10 minutes if not completed."
    )


async def auth_result() -> str:
    """Return the outcome of the most recent browser redirect.

    Useful when ``workboard_auth_status_tool`` still reports no token: this
    says whether a redirect arrived at all and what happened to it.
    """
    recorded = get_pending_login().outcome
    if recorded is None:
        return "No authorization redirect has been received since this server started."
    return recorded


async def finish_callback(query: Mapping[str, str]) -> CallbackOutcome:
    """Complete a browser authorization from WorkBoard's redirect.

    The state is checked before anything else, so a request this server did
    not ask for changes nothing. WorkBoard also appends ``success=1``; the code
    and state are what count, so it is ignored.

    Args:
        query: The redirect's query parameters: ``code`` and ``state`` on
            approval, ``error`` (with ``state``) on denial.

    Returns:
        The outcome to render. Its text never contains a credential or the
        authorization code, and the same text is recorded for
        ``workboard_auth_result_tool``.
    """
    pending = get_pending_login()
    state = query.get("state")
    code = query.get("code")
    error = query.get("error")

    if any(len(value or "") > CALLBACK_PARAM_MAX_LENGTH for value in (state, code, error)):
        return CallbackOutcome(FAILED_HEADING, "Redirect parameters are too long", 400)

    # A stray hit with nothing in flight must not overwrite the outcome of a
    # real authorization, so only failures against an issued state are recorded.
    was_in_progress = pending.in_progress
    try:
        pending.verify(state)
    except AuthenticationError as exc:
        if was_in_progress:
            pending.record(f"Authorization failed: {exc}")
        return CallbackOutcome(FAILED_HEADING, str(exc), 400)

    if error or not code or not state:
        detail = (
            f"WorkBoard denied authorization: {error}"
            if error
            else "WorkBoard returned no authorization code"
        )
        pending.record(f"Authorization failed: {detail}")
        return CallbackOutcome(FAILED_HEADING, detail, 400)

    try:
        config = get_config()
        client_id = config.client_id
        client_secret = config.client_secret
        token_store = config.token_store
        redirect_uri = config.oauth_redirect_uri
        if client_id is None or client_secret is None or token_store is None or not redirect_uri:
            raise ConfigurationError("Server is not configured for OAuth browser authorization")
        # The exchange is a blocking HTTP call; keep it off the event loop.
        await run_in_threadpool(
            complete_login,
            client_id,
            client_secret,
            token_store,
            code=code,
            state=state,
            redirect_uri=redirect_uri,
        )
    except UserError as exc:
        pending.record(f"Authorization failed: {exc}")
        return CallbackOutcome(FAILED_HEADING, str(exc), 400)

    pending.record(f"Authorization succeeded. Tokens stored at {token_store.path}.")
    logger.info("Browser authorization completed")
    return CallbackOutcome("WorkBoard authorization complete", "You can close this tab.", 200)
