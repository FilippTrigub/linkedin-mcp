"""Test for stop_auth_server tool."""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_stop_auth_server():
    """Test the stop_auth_server MCP tool."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "linkedin_mcp"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            result = await session.call_tool("stop_auth_server")
            print(f"Stop auth server result: {result}")


if __name__ == "__main__":
    asyncio.run(test_stop_auth_server())
