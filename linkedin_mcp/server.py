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
        auth_url, expected_state = await auth_client.get_authorization_url()
        
        if ctx:
            ctx.info("Opening browser for authentication...")
        
        # Open browser
        if not webbrowser.open(auth_url):
            raise RuntimeError("Failed to open browser. Please visit the URL manually: " + auth_url)

        logger.info("Waiting for authentication callback...")
        if ctx:
            ctx.info("Waiting for authentication callback...")
            
        # Wait for callback
        code, state = await callback_server.wait_for_callback()
        
        if not code or not state:
            raise AuthError("Authentication failed - no callback received")
            
        if state != expected_state:
            raise AuthError("Invalid state parameter")
            
        if ctx:
            ctx.info("Exchanging authorization code for tokens...")
            
        # Exchange code for tokens
        tokens = await auth_client.exchange_code(code)
        if not tokens:
            raise AuthError("Failed to exchange code for tokens")
            
        if ctx:
            ctx.info("Getting user info...")
            
        # Get and save user info
        logger.info("Getting user info & saving tokens...")
        user_info = await auth_client.get_user_info()
        auth_client.save_tokens(user_info.sub)
        
        logger.info("Successfully authenticated with LinkedIn!")
        return "Successfully authenticated with LinkedIn!"

    except Exception as e:
        error_msg = f"Authentication failed: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    finally:
        # Ensure server is stopped
        if callback_server:
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
            if ctx:
                ctx.info("Not authenticated. Please authenticate first.")
            raise RuntimeError("Not authenticated. Please authenticate first.")

        # Prepare media requests if files are provided
        media_requests = None
        if media_files:
            media_requests = []
            for i, file_path in enumerate(media_files):
                ctx.info(f"Processing media file: {file_path}, "
                            f"title: {media_titles[i] if media_titles and i < len(media_titles) else None}")
                media_requests.append(MediaRequest(
                    file_path=file_path,
                    title=media_titles[i] if media_titles and i < len(media_titles) else None,
                    description=media_descriptions[i] if media_descriptions and i < len(media_descriptions) else None
                ))

        # Create post request
        post_request = PostRequest(
            text=text,
            visibility=visibility,
            media=media_requests
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


def main():
    """Main function for running the LinkedIn server."""
    load_dotenv()
    logger.info("Starting LinkedIn server...")
    mcp.run()


if __name__ == "__main__":
    main()