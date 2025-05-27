"""Test for complete_authentication tool."""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_complete_authentication():
    """Test the complete_authentication MCP tool."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "linkedin_mcp"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            try:
                result = await session.call_tool("complete_authentication")
                print(f"Complete authentication result: {result}")
            except Exception as e:
                print(f"Complete authentication error (expected if no pending auth): {e}")


if __name__ == "__main__":
    asyncio.run(test_complete_authentication())
