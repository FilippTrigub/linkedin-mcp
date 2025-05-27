"""Test for check_auth_status tool."""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_check_auth_status():
    """Test the check_auth_status MCP tool."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "linkedin_mcp"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            result = await session.call_tool("check_auth_status")
            print(f"Auth status result: {result}")


if __name__ == "__main__":
    asyncio.run(test_check_auth_status())
