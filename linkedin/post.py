"""LinkedIn post management implementation."""
from typing import Optional
import logging
import httpx
from pydantic import BaseModel

from config.settings import settings
from linkedin.auth import LinkedInOAuth

logger = logging.getLogger(__name__)

class PostCreationError(Exception):
    """Raised when post creation fails."""
    pass

class PostRequest(BaseModel):
    """LinkedIn post request model."""
    text: str
    visibility: str = "PUBLIC"  # PUBLIC or CONNECTIONS

class PostVisibility:
    """Valid post visibility values."""
    PUBLIC = "PUBLIC"
    CONNECTIONS = "CONNECTIONS"

class PostManager:
    """Manager for LinkedIn posts."""

    def __init__(self, auth_client: LinkedInOAuth) -> None:
        """Initialize the post manager.

        Args:
            auth_client: LinkedIn auth client for authentication
        """
        self.auth_client = auth_client

    @property
    def _headers(self) -> dict:
        """Get request headers with current auth token."""
        if not self.auth_client.access_token:
            raise PostCreationError("Not authenticated")

        return {
            "Authorization": f"Bearer {self.auth_client.access_token}",
            "X-Restli-Protocol-Version": settings.RESTLI_PROTOCOL_VERSION,
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "Content-Type": "application/json"
        }

    async def create_post(self, post_request: PostRequest) -> str:
        """Create a new LinkedIn post.

        Args:
            post_request: Post creation request

        Returns:
            Post ID from LinkedIn

        Raises:
            PostCreationError: If post creation fails
        """
        logger.info(f"Creating LinkedIn post with visibility: {post_request.visibility}")
        # Validate visibility
        if post_request.visibility not in (PostVisibility.PUBLIC, PostVisibility.CONNECTIONS):
            raise PostCreationError("Invalid visibility value")

        # Validate text is not empty
        if not post_request.text.strip():
            raise PostCreationError("Post text cannot be empty")

        # Ensure we have a user ID
        if not self.auth_client.user_id:
            raise PostCreationError("No authenticated user")

        payload = {
            "author": f"urn:li:person:{self.auth_client.user_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post_request.text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": post_request.visibility
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    str(settings.LINKEDIN_POST_URL),
                    headers=self._headers,
                    json=payload
                )
                response.raise_for_status()

                # Get post ID from response header
                post_id = response.headers.get("x-restli-id")
                if not post_id:
                    raise PostCreationError("No post ID returned from LinkedIn")

                logger.info(f"Successfully created LinkedIn post with ID: {post_id}")
                return post_id

        except httpx.HTTPError as e:
            error_msg = f"Failed to create post: {str(e)}"
            if e.response:
                error_msg += f" Response: {e.response.text}"
            logger.error(error_msg)
            raise PostCreationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error creating post: {str(e)}"
            logger.error(error_msg)
            raise PostCreationError(error_msg) from e