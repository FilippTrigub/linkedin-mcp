"""Test for create_post tool."""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from linkedin_mcp.linkedin.post import PostVisibility


async def test_create_post():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "linkedin_mcp"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("create_post", {
                "text": "Test post from MCP client",
                "visibility": PostVisibility.PUBLIC
            })
            print(f"Post creation result: {result}")


if __name__ == "__main__":
    asyncio.run(test_create_post())
