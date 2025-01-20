"""OpenID Connect authentication implementation."""
from typing import Optional, Dict, Any
import httpx
from jose import jwt
from pydantic import BaseModel

from config.settings import settings

class UserInfo(BaseModel):
    """OpenID Connect UserInfo response model."""
    sub: str
    name: str
    given_name: str
    family_name: str
    picture: Optional[str] = None
    locale: Optional[str] = None
    email: Optional[str] = None
    email_verified: Optional[bool] = None

class LinkedInOIDC:
    """LinkedIn OpenID Connect client."""

    def __init__(self) -> None:
        """Initialize the OIDC client."""
        self.client_id = settings.LINKEDIN_CLIENT_ID.get_secret_value()
        self.client_secret = settings.LINKEDIN_CLIENT_SECRET.get_secret_value()
        self.redirect_uri = str(settings.LINKEDIN_REDIRECT_URI)

    async def get_authorization_url(self, state: str) -> str:
        """Get the authorization URL for the OAuth2 flow."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": "openid profile email w_member_social"
        }
        return f"{settings.LINKEDIN_AUTH_URL}?{httpx.QueryParams(params)}"

    async def get_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
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
            return response.json()

    async def get_user_info(self, access_token: str) -> UserInfo:
        """Get user info from LinkedIn."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                str(settings.LINKEDIN_USERINFO_URL),
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return UserInfo(**response.json())