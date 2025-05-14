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
        logger.debug(f"Token storage path: {settings.TOKEN_STORAGE_PATH}")

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
        logger.debug(f"Saving tokens to: {token_path}")
        try:
            with open(token_path, 'w') as f:
                json.dump(self._tokens.model_dump(), f)
            logger.info(f"Tokens saved successfully for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to save tokens: {str(e)}")
            raise AuthError(f"Failed to save authentication tokens: {str(e)}")

    def load_tokens(self, user_id: str) -> bool:
        """Load tokens from file if they exist."""
        token_path = self._get_token_path(user_id)
        logger.debug(f"Attempting to load tokens from: {token_path}")
        
        if not os.path.exists(token_path):
            logger.info(f"No token file found for user: {user_id}")
            return False

        try:
            with open(token_path) as f:
                token_data = json.load(f)
                self._tokens = OAuthTokens(**token_data)
            logger.info(f"Tokens loaded successfully for user: {user_id}")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Invalid token file format: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to load tokens for user {user_id}: {str(e)}")
            return False

    async def get_authorization_url(self) -> tuple[str, str]:
        """Get the authorization URL for the OAuth2 flow."""
        state = secrets.token_urlsafe()
        logger.debug(f"Generated state parameter: {state}")

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": " ".join(settings.LINKEDIN_SCOPES)
        }

        auth_url = f"{settings.LINKEDIN_AUTH_URL}?{httpx.QueryParams(params)}"
        logger.debug(f"Authorization URL parameters: response_type=code, client_id=REDACTED, redirect_uri={self.redirect_uri}, scope={settings.LINKEDIN_SCOPES}")
        return auth_url, state

    async def exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for tokens."""
        logger.info("Exchanging authorization code for tokens")
        try:
            async with httpx.AsyncClient() as client:
                logger.debug(f"Sending token request to: {settings.LINKEDIN_TOKEN_URL}")
                
                data = {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
                
                logger.debug(f"Token request parameters: grant_type=authorization_code, code=REDACTED, redirect_uri={self.redirect_uri}")
                
                response = await client.post(
                    str(settings.LINKEDIN_TOKEN_URL),
                    data=data
                )
                
                if response.status_code != 200:
                    logger.error(f"Token request failed: {response.status_code} - {response.text}")
                    raise AuthError(f"Token request failed with status: {response.status_code}")
                
                response.raise_for_status()
                
                # Parse tokens from response
                token_data = response.json()
                logger.debug("Token response received successfully")
                
                # Store the tokens
                self._tokens = OAuthTokens(**token_data)
                logger.info("Tokens parsed and stored in memory")
                
                return self._tokens
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during token exchange: {str(e)}")
            raise AuthError(f"Failed to exchange code for tokens: HTTP error {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error during token exchange: {str(e)}")
            raise AuthError(f"Failed to exchange code for tokens: Request error - {str(e)}")
        except Exception as e:
            logger.error(f"Error during token exchange: {str(e)}")
            raise AuthError(f"Failed to exchange code for tokens: {str(e)}")

    async def get_user_info(self) -> UserInfo:
        """Get user info from LinkedIn."""
        logger.info("Getting user info from LinkedIn")
        
        if not self._tokens:
            logger.error("Not authenticated - no access token available")
            raise AuthError("Not authenticated")

        try:
            async with httpx.AsyncClient() as client:
                logger.debug(f"Sending user info request to: {settings.LINKEDIN_USERINFO_URL}")
                
                response = await client.get(
                    str(settings.LINKEDIN_USERINFO_URL),
                    headers={"Authorization": f"Bearer {self._tokens.access_token}"}
                )
                
                if response.status_code != 200:
                    logger.error(f"User info request failed: {response.status_code} - {response.text}")
                    raise AuthError(f"User info request failed with status: {response.status_code}")
                
                response.raise_for_status()
                
                # Parse user info from response
                user_data = response.json()
                logger.debug("User info response received successfully")
                
                # Store the user info
                self._user_info = UserInfo(**user_data)
                logger.info(f"User info retrieved for user: {self._user_info.sub}")
                
                return self._user_info
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during user info request: {str(e)}")
            raise AuthError(f"Failed to get user info: HTTP error {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error during user info request: {str(e)}")
            raise AuthError(f"Failed to get user info: Request error - {str(e)}")
        except Exception as e:
            logger.error(f"Error during user info request: {str(e)}")
            raise AuthError(f"Failed to get user info: {str(e)}")

    @property
    def access_token(self) -> Optional[str]:
        """Get the current access token if we have one."""
        return self._tokens.access_token if self._tokens else None

    @property
    def user_id(self) -> Optional[str]:
        """Get the current user ID if we have one."""
        return self._user_info.sub if self._user_info else None
