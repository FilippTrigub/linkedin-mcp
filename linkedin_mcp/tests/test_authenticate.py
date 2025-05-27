"""Test for authenticate tool."""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_authenticate():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "linkedin_mcp"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            result = await session.call_tool("authenticate")
            print(f"Authentication result: {result}")


if __name__ == "__main__":
    asyncio.run(test_authenticate())
