"""MCP server for LinkedIn integration."""
import logging
import webbrowser
from typing import List

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from pydantic import FilePath

from .linkedin.auth import LinkedInOAuth, AuthError
from .linkedin.post import PostManager, PostRequest, PostCreationError, MediaRequest, PostVisibility
from .callback_server import LinkedInCallbackServer
from .utils.logging import configure_logging
from .config.settings import settings

# Configure logging
configure_logging(
    log_level=settings.LOG_LEVEL,
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


@mcp.tool()
async def authenticate(ctx: Context = None) -> str:
    """Start LinkedIn authentication flow and handle callback automatically.

    Returns:
        Success message after authentication
    """
    logger.info("Starting LinkedIn authentication flow...")
    callback_server = None

    try:
        # Start callback server
        callback_server = LinkedInCallbackServer(port=3000)
        await callback_server.start()

        # Get auth URL
        logger.debug("Getting authorization URL from LinkedIn")
        auth_url, expected_state = await auth_client.get_authorization_url()
        logger.debug(f"Authorization URL generated with state: {expected_state}")

        if ctx:
            ctx.info("Opening browser for authentication...")

        # Open browser
        logger.info(f"Opening browser to: {auth_url}")
        if not webbrowser.open(auth_url):
            error_msg = "Failed to open browser. Please visit the URL manually: " + auth_url
            logger.error(error_msg)
            if ctx:
                ctx.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info("Waiting for authentication callback...")
        if ctx:
            ctx.info("Waiting for authentication callback...")

        # Add debug info for event status
        logger.debug(f"Auth received event status before wait: {callback_server.auth_received.is_set()}")

        try:
            import asyncio
            logger.debug("Current event loop: %s", asyncio.get_running_loop())
        except RuntimeError as e:
            logger.warning(f"Error getting event loop: {str(e)}")

        # Wait for callback with detailed error handling
        logger.debug("Calling wait_for_callback with 120 second timeout")
        code, state = await callback_server.wait_for_callback(timeout=120)  # Reduced timeout for better user experience

        logger.debug(f"Auth received event status after wait: {callback_server.auth_received.is_set()}")
        logger.debug(f"Callback result received: code={code is not None}, state={state is not None}")

        # Check code and state, providing detailed log messages
        if not code:
            logger.error("No authorization code received from callback")
            raise AuthError("Authentication failed - no authorization code received")

        if not state:
            logger.error("No state parameter received from callback")
            raise AuthError("Authentication failed - no state parameter received")

        if state != expected_state:
            logger.error(f"State mismatch. Expected: {expected_state}, Got: {state}")
            raise AuthError(f"Invalid state parameter: expected {expected_state}, got {state}")

        logger.debug(f"State parameter matches expected value: {state}")

        if ctx:
            ctx.info("Exchanging authorization code for tokens...")

        # Exchange code for tokens
        logger.info("Exchanging authorization code for tokens")
        tokens = await auth_client.exchange_code(code)
        if not tokens:
            logger.error("Failed to exchange code for tokens")
            raise AuthError("Failed to exchange authorization code for tokens")

        logger.debug("Successfully obtained tokens from authorization code")

        if ctx:
            ctx.info("Getting user info...")

        # Get and save user info
        logger.info("Getting user info & saving tokens...")
        user_info = await auth_client.get_user_info()
        logger.debug(f"User info retrieved: {user_info.sub}")

        auth_client.save_tokens(user_info.sub)
        logger.info("Tokens saved successfully")

        success_msg = f"Successfully authenticated with LinkedIn as {user_info.name}!"
        logger.info(success_msg)
        return success_msg

    except AuthError as e:
        error_msg = f"Authentication error: {str(e)}"
        logger.error(error_msg)
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Authentication failed: {str(e)}"
        logger.exception("Unexpected error during authentication")
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)
    finally:
        # Ensure server is stopped
        if callback_server:
            logger.debug("Stopping callback server in finally block")
            callback_server.stop()


@mcp.tool()
async def create_post(
        text: str,
        media_files: List[FilePath] = None,
        media_titles: List[str] = None,
        media_descriptions: List[str] = None,
        visibility: PostVisibility = "PUBLIC",
        ctx: Context = None
) -> str:
    """Create a new post on LinkedIn.

    Args:
        text: The content of your post
        media_files: List of paths to media files to attach (images or videos)
        media_titles: Optional titles for media attachments
        media_descriptions: Optional descriptions for media attachments
        visibility: Post visibility (PUBLIC or CONNECTIONS)
        ctx: MCP Context for progress reporting

    Returns:
        Success message with post ID
    """
    logger.info("Creating LinkedIn post...")
    try:
        if ctx:
            ctx.info(f"Creating LinkedIn post with visibility: {visibility}")

        if not auth_client.is_authenticated:
            error_msg = "Not authenticated. Please authenticate first."
            logger.error(error_msg)
            if ctx:
                ctx.error(error_msg)
            raise RuntimeError(error_msg)

        # Prepare media requests if files are provided
        media_requests = None
        if media_files:
            media_requests = []
            for i, file_path in enumerate(media_files):
                title = media_titles[i] if media_titles and i < len(media_titles) else None
                description = media_descriptions[i] if media_descriptions and i < len(media_descriptions) else None

                logger.debug(f"Processing media file: {file_path}, title: {title}")
                if ctx:
                    ctx.info(f"Processing media file: {file_path}, title: {title}")

                media_requests.append(MediaRequest(
                    file_path=file_path,
                    title=title,
                    description=description
                ))

        # Create post request
        post_request = PostRequest(
            text=text,
            visibility=visibility,
            media=media_requests
        )

        # Create the post
        logger.info("Sending post to LinkedIn API")
        post_id = await post_manager.create_post(post_request)
        success_msg = f"Successfully created LinkedIn post with ID: {post_id}"
        logger.info(success_msg)

        return success_msg

    except (AuthError, PostCreationError) as e:
        error_msg = str(e)
        logger.error(error_msg)
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception("Unexpected error during post creation")
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


def main():
    """Main function for running the LinkedIn server."""
    load_dotenv()
    logger.info("Starting LinkedIn server...")
    mcp.run()
