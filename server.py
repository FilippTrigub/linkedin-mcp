"""LinkedIn MCP Server implementation."""
import logging
import os
from typing import Optional
from mcp.server.fastmcp import FastMCP, Context

from linkedin.auth import LinkedInOIDC, UserInfo
from linkedin.post import PostManager, PostRequest, PostCreationError
from config.settings import settings

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("LinkedIn Integration")

# Initialize OIDC client
oidc_client = LinkedInOIDC()

@mcp.tool()
async def authenticate(ctx: Context) -> str:
    """Authenticate with LinkedIn using OpenID Connect.
    
    Returns:
        Success message with user info
    """
    try:
        # In a real implementation, we would handle the OAuth flow properly
        # For now, we'll use environment variables for demo purposes
        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if not access_token:
            raise ValueError("LINKEDIN_ACCESS_TOKEN not set in environment")
        
        user_info = await oidc_client.get_user_info(access_token)
        return f"Authenticated as {user_info.name} ({user_info.email})"
    except Exception as e:
        logger.error("Authentication failed: %s", str(e))
        raise

@mcp.tool()
async def create_post(text: str, ctx: Context, visibility: str = "PUBLIC") -> str:
    """Create a new post on LinkedIn.
    
    Args:
        text: Post content
        visibility: Post visibility (PUBLIC or CONNECTIONS)
        
    Returns:
        Success message with post ID
    """
    try:
        # In a real implementation, we would get these from the authenticated session
        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        person_id = os.getenv("LINKEDIN_PERSON_ID")
        
        if not access_token or not person_id:
            raise ValueError("LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_ID must be set")
            
        post_manager = PostManager(access_token, person_id)
        post_request = PostRequest(text=text, visibility=visibility)
        
        post_id = await post_manager.create_post(post_request)
        return f"Post created successfully with ID: {post_id}"
    except PostCreationError as e:
        logger.error("Post creation failed: %s", str(e))
        raise
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        raise

if __name__ == "__main__":
    mcp.run()