"""LinkedIn post management implementation."""
from typing import Optional
import httpx
from pydantic import BaseModel

from config.settings import settings

class PostCreationError(Exception):
    """Raised when post creation fails."""
    pass

class PostRequest(BaseModel):
    """LinkedIn post request model."""
    text: str
    visibility: str = "PUBLIC"  # PUBLIC or CONNECTIONS

class PostManager:
    """Manager for LinkedIn posts."""

    def __init__(self, access_token: str, person_id: str) -> None:
        """Initialize the post manager.
        
        Args:
            access_token: LinkedIn access token
            person_id: LinkedIn person URN ID
        """
        self.access_token = access_token
        self.person_id = person_id
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": settings.RESTLI_PROTOCOL_VERSION,
            "LinkedIn-Version": settings.LINKEDIN_VERSION
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
        payload = {
            "author": f"urn:li:person:{self.person_id}",
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
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                # LinkedIn returns the post ID in the X-RestLi-Id header
                return response.headers.get("X-RestLi-Id", "")
        except httpx.HTTPError as e:
            raise PostCreationError(f"Failed to create post: {str(e)}") from e