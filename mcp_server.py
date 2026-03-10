# mcp_server.py
from mcp.server.fastmcp import FastMCP

# Create MCP server
mcp = FastMCP("DemoMCP", json_response=True)

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

@mcp.resource("greeting://{name}")
def greeting(name: str) -> str:
    """Return a greeting string for a given name."""
    return f"Hello, {name}! (from MCP)"

if __name__ == "__main__":
    # Streamable HTTP transport (served at http://localhost:8000/mcp)
    mcp.run(transport="streamable-http")