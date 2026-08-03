"""Secure MCP server for WorkBoard OKR and strategy execution platform."""

import argparse
import os
import sys

from .server import mcp

__version__ = "0.8.0"
__all__ = ["main", "mcp"]


def _run_login(args: argparse.Namespace) -> None:
    """Handle the login subcommand."""
    from pydantic import SecretStr

    from .auth import TokenStore, run_login_flow
    from .errors import AuthenticationError

    client_id = os.environ.get("WORKBOARD_CLIENT_ID")
    client_secret = os.environ.get("WORKBOARD_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "Error: WORKBOARD_CLIENT_ID and WORKBOARD_CLIENT_SECRET must be set for OAuth login.",
            file=sys.stderr,
        )
        sys.exit(1)

    token_store = TokenStore()
    try:
        run_login_flow(
            client_id=client_id,
            client_secret=SecretStr(client_secret),
            token_store=token_store,
            callback_port=args.port,
        )
    except AuthenticationError as e:
        print(f"Login failed: {e}", file=sys.stderr)
        sys.exit(1)


def _run_server(args: argparse.Namespace) -> None:
    """Handle the serve subcommand (default)."""
    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


def main() -> None:
    """Main entry point for the MCP server."""
    parser = argparse.ArgumentParser(description="MCP server for WorkBoard OKR")
    subparsers = parser.add_subparsers(dest="command")

    # login subcommand
    login_parser = subparsers.add_parser(
        "login",
        help="Authenticate with WorkBoard via OAuth 2",
    )
    login_parser.add_argument(
        "--port",
        type=int,
        default=8963,
        help="Local callback server port (default: 8963)",
    )

    # serve subcommand (also the default when no subcommand given)
    serve_parser = subparsers.add_parser("serve", help="Run the MCP server")
    for p in (parser, serve_parser):
        p.add_argument(
            "--transport",
            choices=["stdio", "sse", "streamable-http"],
            default="stdio",
            help="Transport protocol (default: stdio)",
        )
        p.add_argument(
            "--host",
            default="127.0.0.1",
            help="Host to bind to for HTTP transports (default: 127.0.0.1)",
        )
        p.add_argument(
            "--port",
            type=int,
            default=8000,
            help="Port to bind to for HTTP transports (default: 8000)",
        )

    args = parser.parse_args()

    if args.command == "login":
        _run_login(args)
    else:
        _run_server(args)
