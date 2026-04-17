"""Stdio MCP server with minimal sample tools (migrated from root `mcp_server.py`)."""

from mcp.server.fastmcp import FastMCP

server = FastMCP("iso-agent-local-tools")


@server.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@server.tool()
def echo(text: str) -> str:
    """Return the input text."""
    return text


def main() -> None:
    """Run MCP over stdio (entry point for `iso-mcp-stdio`)."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
