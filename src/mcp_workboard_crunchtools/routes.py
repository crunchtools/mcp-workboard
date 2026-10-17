"""HTTP routes served alongside the MCP transport.

``server.py`` holds the MCP tools; this module holds the one plain HTTP route,
WorkBoard's OAuth redirect target. Importing it registers the route on the
shared ``mcp`` instance, which the package ``__init__`` does.
"""

from starlette.requests import Request
from starlette.responses import HTMLResponse

from .server import mcp
from .tools import finish_callback

__all__ = ["mcp", "oauth_callback"]


@mcp.custom_route("/callback", methods=["GET"])
async def oauth_callback(request: Request) -> HTMLResponse:
    """Receive WorkBoard's redirect and render what happened.

    This is the whole reason the flow needs no copy and paste: WorkBoard sends
    the browser here, and the exchange happens server-side before the page
    renders. The work is in ``tools.auth.finish_callback``; this route only
    hands it the query string and turns the outcome into a page.

    Args:
        request: The redirect from WorkBoard. Its query carries ``code`` and
            ``state`` on approval, or ``error`` on denial, plus ``success``.

    Returns:
        A short HTML page for the human in the browser: 200 when the tokens
        were stored, 400 with the reason otherwise. It never contains a
        credential or the authorization code.
    """
    outcome = await finish_callback(request.query_params)
    return HTMLResponse(outcome.page(), status_code=outcome.status_code)
