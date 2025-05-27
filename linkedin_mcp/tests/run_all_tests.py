"""Run all MCP tool tests."""
import asyncio
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from linkedin_mcp.tests.test_authenticate import test_authenticate
from linkedin_mcp.tests.test_complete_authentication import test_complete_authentication
from linkedin_mcp.tests.test_check_auth_status import test_check_auth_status
from linkedin_mcp.tests.test_stop_auth_server import test_stop_auth_server
from linkedin_mcp.tests.test_create_post import test_create_post


async def run_all_tests():
    """Run all MCP tool tests."""
    tests = [
        ("authenticate", test_authenticate),
        ("check_auth_status", test_check_auth_status),
        ("stop_auth_server", test_stop_auth_server),
        ("complete_authentication", test_complete_authentication),
        ("create_post", test_create_post),
    ]
    
    print("=" * 60)
    print("Running all LinkedIn MCP tool tests")
    print("=" * 60)
    
    for test_name, test_func in tests:
        print(f"\n--- Testing {test_name} ---")
        try:
            await test_func()
        except Exception as e:
            print(f"Test {test_name} failed: {e}")
        print("-" * 30)
    
    print("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
