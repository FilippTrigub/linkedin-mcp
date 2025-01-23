"""LinkedIn post management implementation."""
from enum import Enum
import logging
import mimetypes
from pathlib import Path
from typing import Optional, List
import httpx
from pydantic import BaseModel, FilePath

from ..config.settings import settings
from ..linkedin.auth import LinkedInOAuth

logger = logging.getLogger(__name__)

class PostCreationError(Exception):
    """Raised when post creation fails."""
    pass

class MediaUploadError(Exception):
    """Raised when media upload fails."""
    pass

class MediaCategory(str, Enum):
    """Valid media categories."""
    NONE = "NONE"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    ARTICLE = "ARTICLE"

class PostVisibility(str, Enum):
    """Valid post visibility values."""
    PUBLIC = "PUBLIC"
    CONNECTIONS = "CONNECTIONS"

class MediaRequest(BaseModel):
    """Media attachment request."""
    file_path: FilePath
    title: Optional[str] = None
    description: Optional[str] = None

class PostMediaItem:
    file_path: Path
    title: str = ""
    description: str = ""

class PostRequest(BaseModel):
    """LinkedIn post request model."""
    text: str
    visibility: PostVisibility = PostVisibility.PUBLIC
    media: Optional[List[MediaRequest]] = None

class PostManager:
    """Manager for LinkedIn posts."""

    def __init__(self, auth_client: LinkedInOAuth) -> None:
        """Initialize the post manager."""
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

    async def _register_upload(self, file_path: Path) -> tuple[str, str, str]:
        """Register media upload with LinkedIn.

        Returns:
            Tuple of (upload_url, asset_id, media_type)
        """
        # Determine media type from file extension
        media_type = mimetypes.guess_type(file_path)[0]
        if not media_type:
            raise MediaUploadError(f"Unsupported file type: {file_path}")

        recipe_type = "feedshare-image" if media_type.startswith("image/") else "feedshare-video"

        register_data = {
            "registerUploadRequest": {
                "recipes": [f"urn:li:digitalmediaRecipe:{recipe_type}"],
                "owner": f"urn:li:person:{self.auth_client.user_id}",
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }]
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                str(settings.LINKEDIN_ASSET_REGISTER_URL),
                headers=self._headers,
                json=register_data
            )
            response.raise_for_status()
            data = response.json()

            upload_url = data["value"]["uploadMechanism"][
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
            ]["uploadUrl"]

            asset_id = data["value"]["asset"]

            return upload_url, asset_id, recipe_type

    async def _upload_media(self, file_path: Path, upload_url: str, media_type: str) -> None:
        """Upload media file to LinkedIn."""
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                headers = {
                    "Authorization": f"Bearer {self.auth_client.access_token}",
                    "media-type-family": "STILLIMAGE" if media_type == "feedshare-image" else "VIDEO"
                }
                response = await client.post(
                    upload_url,
                    headers=headers,
                    content=f.read()
                )
                response.raise_for_status()

    async def create_post(self, post_request: PostRequest) -> str:
        """Create a new LinkedIn post with optional media attachments."""
        logger.info(f"Creating LinkedIn post with visibility: {post_request.visibility}")

        if not post_request.text.strip():
            logger.error("Post text cannot be empty")
            raise PostCreationError("Post text cannot be empty")

        if not self.auth_client.user_id:
            logger.error("No authenticated user")
            raise PostCreationError("No authenticated user")

        # Build post payload
        payload = {
            "author": f"urn:li:person:{self.auth_client.user_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post_request.text
                    },
                    "shareMediaCategory": MediaCategory.NONE.value
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": post_request.visibility.value
            }
        }

        # Handle media attachments
        if post_request.media:
            media_list = []
            recipe_type = None
            for media_item in post_request.media:
                # Register and upload each media file
                upload_url, asset_id, recipe_type = await self._register_upload(media_item.file_path)
                await self._upload_media(media_item.file_path, upload_url, recipe_type)

                # Add media to post payload with required fields
                media_list.append({
                    "status": "READY",
                    "media": asset_id,
                    "title": {"text": media_item.title or f"Image {len(media_list) + 1}"},
                    "description": {"text": media_item.description or f"Image {len(media_list) + 1} description"}
                })

            # Update payload with media
            payload["specificContent"]["com.linkedin.ugc.ShareContent"].update({
                "shareMediaCategory": (
                    MediaCategory.IMAGE.value if recipe_type == "feedshare-image"
                    else MediaCategory.VIDEO.value
                ),
                "media": media_list
            })

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    str(settings.LINKEDIN_POST_URL),
                    headers=self._headers,
                    json=payload
                )
                response.raise_for_status()

                post_id = response.headers.get("x-restli-id")
                if not post_id:
                    logger.error("No post ID returned from LinkedIn")
                    raise PostCreationError("No post ID returned from LinkedIn")

                logger.info(f"Successfully created LinkedIn post with ID: {post_id}")
                return post_id

        except httpx.HTTPError as e:
            error_msg = f"Failed to create post: {str(e)}"
            logger.error(error_msg)
            raise PostCreationError(error_msg) from e