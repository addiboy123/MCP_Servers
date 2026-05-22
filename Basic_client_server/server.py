# server.py
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Create an MCP server
mcp = FastMCP(
    name="Calculator",
    host="0.0.0.0",  # only used for SSE transport (localhost)
    port=8050,  # only used for SSE transport (set this to any port)
    stateless_http=True,
)

# Simple tool
@mcp.tool()
def say_hello(name: str) -> str:
    """Say hello to someone

    Args:
        name: The person's name to greet
    """
    return f"Hello, {name}! Nice to meet you."

# Add a simple calculator tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b


''''
MCP supports three transport modes:
1. stdio: This is the default mode and is suitable for local development or integrating with claude desktop. It uses standard input and output for communication.
2. sse: This mode uses Server-Sent Events (SSE) for communication which is based on HTTP. It is suitable for web applications. When using this mode, the server will listen on the specified host and port. (http://127.0.0.1:8050 in this example)
3. streamable-http: This mode uses a streamable HTTP transport for communication. It is suitable for web applications and allows for real-time updates. When using this mode, the server will listen on the specified host and port.
'''

# Run the server
if __name__ == "__main__":
    transport = "sse"
    if transport == "stdio":
        print("Running server with stdio transport")
        mcp.run(transport="stdio")
    elif transport == "sse":
        print("Running server with SSE transport")
        mcp.run(transport="sse")
    elif transport == "streamable-http":
        print("Running server with Streamable HTTP transport")
        mcp.run(transport="streamable-http")
    else:
        raise ValueError(f"Unknown transport: {transport}")