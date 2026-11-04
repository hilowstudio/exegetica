"""A stand-in MCP server for tests/test_bridge.py: one quick tool, one slow tool, one that kills
its own process. Run by the bridge as `python -m tests.fake_mcp_server --transport stdio`."""
import os
import time

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("fake")


@mcp.tool()
def echo(text: str) -> str:
    """Return the text."""
    return text


@mcp.tool()
def slow(seconds: float) -> str:
    """Sleep, blocking the server."""
    time.sleep(seconds)
    return "done"


@mcp.tool()
def die() -> str:
    """End the server process mid-call."""
    os._exit(1)


if __name__ == "__main__":
    mcp.run("stdio")
