"""MCP server for LinkedIn integration."""
import logging
from typing import Dict

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context

from linkedin.auth import LinkedInOAuth, AuthError
from linkedin.post import PostManager, PostRequest, PostCreationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(
    "LinkedInServer",
    dependencies=[
        "httpx",
        "mcp[cli]",
        "pydantic",
        "pydantic-settings",
        "python-dotenv"
    ]
)

# Initialize LinkedIn clients
auth_client = LinkedInOAuth()
post_manager = PostManager(auth_client)

# Store for auth states
auth_states: Dict[str, str] = {}


@mcp.tool()
async def authenticate(ctx: Context = None) -> str:
    """Start LinkedIn authentication flow.

    Returns:
        URL to visit to authenticate
    """
    logger.info("Starting LinkedIn authentication flow...")
    try:
        # Get auth URL and state
        auth_url, state = await auth_client.get_authorization_url()

        # Store state
        auth_states[state] = state

        if ctx:
            ctx.info(f"Please visit this URL to authenticate with LinkedIn: {auth_url}")

        logger.info(f"Generated auth URL: {auth_url}")
        return (f"The user has to visit the following url: \n{auth_url} \n "
                f"Reprint the url, tell the user to visit it to authenticate with LinkedIn "
                f"and then to copy the callback url with the code into the Claude chat. "
                f"Use handle_oauth_callback to finish the authentication process.")
    except Exception as e:
        error_msg = f"Failed to start auth flow: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        logger.error(error_msg)


@mcp.tool()
async def handle_oauth_callback(code: str, state: str, ctx: Context = None) -> str:
    """Handle OAuth callback.

    Args:
        code: Authorization code from LinkedIn
        state: State parameter from callback
        ctx: MCP Context for progress reporting

    Returns:
        Success message
    """
    logger.info("Handling LinkedIn OAuth callback...")
    try:
        # Validate state
        if state not in auth_states:
            raise AuthError("Invalid state parameter")

        # Remove used state
        auth_states.pop(state)

        # Exchange code for tokens
        if ctx:
            ctx.info("Exchanging authorization code for tokens...")

        tokens = await auth_client.exchange_code(code)

        # Get user info
        if ctx:
            ctx.info("Getting user info...")

        user_info = await auth_client.get_user_info()

        # Save tokens
        auth_client.save_tokens(user_info.sub)
        logger.info("Successfully authenticated with LinkedIn!")

        return "Successfully authenticated with LinkedIn!"

    except Exception as e:
        error_msg = f"Authentication failed: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        logger.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool()
async def create_post(text: str, visibility: str = "PUBLIC", ctx: Context = None) -> str:
    """Create a new post on LinkedIn.

    Args:
        text: The content of your post
        visibility: Post visibility (PUBLIC or CONNECTIONS)
        ctx: MCP Context for progress reporting

    Returns:
        Success message with post ID
    """
    logger.info("Creating LinkedIn post...")
    try:
        if ctx:
            ctx.info(f"Creating LinkedIn post with visibility: {visibility}")

        # Check if we need to authenticate
        if not auth_client.is_authenticated:
            if ctx:
                ctx.info("Not authenticated. Please authenticate first using the authenticate tool.")
            raise RuntimeError("Not authenticated. Please authenticate first.")

        # Create post request
        post_request = PostRequest(
            text=text,
            visibility=visibility
        )

        # Create the post
        post_id = await post_manager.create_post(post_request)
        logger.info(f"Successfully created LinkedIn post with ID: {post_id}")

        return f"Successfully created LinkedIn post with ID: {post_id}"

    except (AuthError, PostCreationError) as e:
        error_msg = str(e)
        if ctx:
            ctx.error(error_msg)
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        logger.error(error_msg)
        raise RuntimeError(error_msg)


if __name__ == "__main__":
    load_dotenv()
    logger.info("Starting LinkedIn server...")
    mcp.run()
