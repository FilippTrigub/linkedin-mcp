"""LinkedIn OAuth2 authentication implementation."""
import json
import logging
import os
import secrets
from typing import Optional
import httpx
from pydantic import BaseModel

from ..config.settings import settings

logger = logging.getLogger(__name__)

class AuthError(Exception):
    """Raised when authentication fails."""
    pass

class OAuthTokens(BaseModel):
    """OAuth tokens response model."""
    access_token: str
    expires_in: int
    refresh_token: Optional[str] = None
    refresh_token_expires_in: Optional[int] = None
    scope: str

class UserInfo(BaseModel):
    """LinkedIn UserInfo response model."""
    sub: str
    name: str
    given_name: str
    family_name: str
    picture: str | None = None
    locale: dict | None = None
    email: str | None = None
    email_verified: bool | None = None


class LinkedInOAuth:
    """LinkedIn OAuth2 client."""

    def __init__(self) -> None:
        """Initialize the OAuth client."""
        self.client_id = settings.LINKEDIN_CLIENT_ID.get_secret_value()
        self.client_secret = settings.LINKEDIN_CLIENT_SECRET.get_secret_value()
        self.redirect_uri = str(settings.LINKEDIN_REDIRECT_URI)
        self._tokens: Optional[OAuthTokens] = None
        self._user_info: Optional[UserInfo] = None

        # Create token storage directory if it doesn't exist
        os.makedirs(settings.TOKEN_STORAGE_PATH, exist_ok=True)

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid tokens."""
        return self._tokens is not None

    @staticmethod
    def _get_token_path(user_id: str) -> str:
        """Get path to token file for user."""
        return os.path.join(settings.TOKEN_STORAGE_PATH, f"{user_id}.json")

    def save_tokens(self, user_id: str) -> None:
        """Save tokens to file."""
        if not self._tokens:
            logger.error("No tokens to save")
            return

        token_path = self._get_token_path(user_id)
        with open(token_path, 'w') as f:
            json.dump(self._tokens.model_dump(), f)

    def load_tokens(self, user_id: str) -> bool:
        """Load tokens from file if they exist."""
        token_path = self._get_token_path(user_id)
        if not os.path.exists(token_path):
            return False

        try:
            with open(token_path) as f:
                token_data = json.load(f)
                self._tokens = OAuthTokens(**token_data)
            return True
        except Exception:
            logger.error(f"Failed to load tokens for user: {user_id}")
            return False

    async def get_authorization_url(self) -> tuple[str, str]:
        """Get the authorization URL for the OAuth2 flow."""
        state = secrets.token_urlsafe()

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": " ".join(settings.LINKEDIN_SCOPES)
        }

        auth_url = f"{settings.LINKEDIN_AUTH_URL}?{httpx.QueryParams(params)}"
        return auth_url, state

    async def exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    str(settings.LINKEDIN_TOKEN_URL),
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    }
                )
                response.raise_for_status()
                self._tokens = OAuthTokens(**response.json())
                return self._tokens
        except Exception as e:
            raise AuthError(f"Failed to exchange code for tokens: {str(e)}") from e

    async def get_user_info(self) -> UserInfo:
        """Get user info from LinkedIn."""
        if not self._tokens:
            raise AuthError("Not authenticated")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    str(settings.LINKEDIN_USERINFO_URL),
                    headers={"Authorization": f"Bearer {self._tokens.access_token}"}
                )
                response.raise_for_status()
                self._user_info = UserInfo(**response.json())
                return self._user_info
        except Exception as e:
            raise AuthError(f"Failed to get user info: {str(e)}") from e

    @property
    def access_token(self) -> Optional[str]:
        """Get the current access token if we have one."""
        return self._tokens.access_token if self._tokens else None

    @property
    def user_id(self) -> Optional[str]:
        """Get the current user ID if we have one."""
        return self._user_info.sub if self._user_info else None