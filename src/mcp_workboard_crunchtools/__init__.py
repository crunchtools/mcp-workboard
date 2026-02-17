"""MCP WorkBoard CrunchTools - Secure MCP server for WorkBoard.

A security-focused MCP server for WorkBoard OKR and strategy
execution platform.

Usage:
    # Run directly
    mcp-workboard-crunchtools

    # Or with Python module
    python -m mcp_workboard_crunchtools

    # With uvx
    uvx mcp-workboard-crunchtools

Environment Variables:
    WORKBOARD_API_TOKEN: Required. WorkBoard JWT API token.

Example with Claude Code:
    claude mcp add mcp-workboard-crunchtools \\
        --env WORKBOARD_API_TOKEN=your_token_here \\
        -- uvx mcp-workboard-crunchtools
"""

from .server import mcp

__version__ = "0.1.0"
__all__ = ["main", "mcp"]


def main() -> None:
    """Main entry point for the MCP server."""
    mcp.run()
