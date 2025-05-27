"""MCP server for LinkedIn integration."""
import logging
import webbrowser
from typing import List, Optional

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

# Global callback server for persistent authentication state
_callback_server: Optional[LinkedInCallbackServer] = None
_auth_state: Optional[str] = None

async def _ensure_callback_server() -> LinkedInCallbackServer:
    """Ensure callback server is running and return it."""
    global _callback_server

    if _callback_server is None:
        logger.info("Starting persistent callback server...")
        _callback_server = LinkedInCallbackServer(port=3000)
        await _callback_server.start()
        logger.info("Persistent callback server started")

    return _callback_server


async def _complete_token_exchange(code: str, ctx: Context = None) -> str:
    """Complete the token exchange process and save authentication data.
    
    Args:
        code: Authorization code from LinkedIn
        ctx: MCP Context for progress reporting
        
    Returns:
        Success message with user name
    """
    global _callback_server, _auth_state
    
    if ctx:
        ctx.info("Exchanging authorization code for tokens...")

    # Exchange code for tokens
    logger.info("Exchanging authorization code for tokens")
    tokens = await auth_client.exchange_code(code)
    if not tokens:
        logger.error("Failed to exchange code for tokens")
        raise RuntimeError("Failed to exchange authorization code for tokens")

    logger.debug("Successfully obtained tokens from authorization code")

    if ctx:
        ctx.info("Getting user info...")

    # Get and save user info
    logger.info("Getting user info & saving tokens...")
    user_info = await auth_client.get_user_info()
    logger.debug(f"User info retrieved: {user_info.sub}")

    auth_client.save_tokens(user_info.sub)
    logger.info("Tokens saved successfully")

    # Stop callback server after successful authentication
    _stop_callback_server()
    _auth_state = None

    success_msg = f"Successfully authenticated with LinkedIn as {user_info.name}!"
    logger.info(success_msg)
    return success_msg

def _stop_callback_server() -> None:
    """Stop the persistent callback server."""
    global _callback_server

    if _callback_server is not None:
        logger.info("Stopping persistent callback server")
        _callback_server.stop()
        _callback_server = None
        logger.info("Persistent callback server stopped")


@mcp.tool()
async def authenticate(ctx: Context = None) -> str:
    """Start LinkedIn authentication flow and handle callback automatically.

    Returns:
        Success message after authentication
    """
    global _auth_state

    logger.info("Starting LinkedIn authentication flow...")

    try:
        # Ensure callback server is running
        callback_server = await _ensure_callback_server()

        # Get auth URL
        logger.debug("Getting authorization URL from LinkedIn")
        auth_url, expected_state = await auth_client.get_authorization_url()
        _auth_state = expected_state  # Store state globally
        logger.debug(f"Authorization URL generated with state: {expected_state}")

        if ctx:
            ctx.info("Opening browser for authentication...")

        # Open browser
        logger.info(f"Opening browser to: {auth_url}")
        browser_opened = False
        try:
            browser_opened = webbrowser.open(auth_url)
        except Exception as e:
            logger.warning(f"Exception when trying to open browser: {str(e)}")
            browser_opened = False

        if not browser_opened:
            # Return immediately with URL, but keep server running
            error_msg = f"Failed to open browser. Please visit the URL manually and then call complete_authentication: {auth_url}"
            logger.error(error_msg)
            if ctx:
                ctx.error(error_msg)
            # Don't stop the callback server - let it keep running
            raise RuntimeError(error_msg)

        # Wait for callback with timeout
        logger.info("Waiting for authentication callback...")
        if ctx:
            ctx.info("Waiting for authentication callback...")

        code, state = await callback_server.wait_for_callback(timeout=120)

        # Check if we got the callback
        if not code or not state:
            error_msg = "Authentication timeout - no callback received. Please try again."
            logger.error(error_msg)
            # Don't stop server yet - user might try again
            raise RuntimeError(error_msg)

        # Validate state
        if state != expected_state:
            logger.error(f"State mismatch. Expected: {expected_state}, Got: {state}")
            _stop_callback_server()  # Stop server on security issue
            raise RuntimeError("Authentication failed - invalid state parameter")

        logger.debug(f"State parameter matches expected value: {state}")

        # Complete token exchange and save authentication data
        return await _complete_token_exchange(code, ctx)

    except Exception as e:
        error_msg = f"Authentication failed: {str(e)}"
        logger.exception("Error during authentication")
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool()
async def complete_authentication(ctx: Context = None) -> str:
    """Complete authentication using any pending callback data.

    Returns:
        Success message after authentication
    """
    global _callback_server, _auth_state

    logger.info("Attempting to complete authentication with pending callback...")

    try:
        if not _callback_server:
            error_msg = "No callback server running. Call authenticate first."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        if not _auth_state:
            error_msg = "No pending authentication state. Call authenticate first."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Check if callback was already received
        if _callback_server.auth_received.is_set():
            logger.info("Callback already received, processing...")
            code = _callback_server.server.auth_code
            state = _callback_server.server.state

            if not code or not state:
                error_msg = "Callback received but missing code or state"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Validate state
            if state != _auth_state:
                logger.error(f"State mismatch. Expected: {_auth_state}, Got: {state}")
                _stop_callback_server()
                _auth_state = None
                raise RuntimeError("Authentication failed - invalid state parameter")

            logger.debug(f"State parameter matches expected value: {state}")

            # Complete token exchange and save authentication data
            return await _complete_token_exchange(code, ctx)
        else:
            error_msg = "No callback received yet. Please complete authentication in browser first."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    except Exception as e:
        error_msg = f"Authentication completion failed: {str(e)}"
        logger.exception("Error during authentication completion")
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)

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
