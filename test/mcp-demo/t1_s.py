from fastmcp import FastMCP

mcp = FastMCP(
    name="test_sse_s",
    dependencies=["requests"],
    host="127.0.0.1",
    port=9001
)

@mcp.tool(description="Adds two integer numbers together.")
def add(a: int, b: int) -> int:
    return a + b


if __name__ == "__main__":
    mcp.run(
        transport="sse",
    )