"""MCP LinkedIn server configuration."""
import os

from dotenv import load_dotenv
from pydantic import HttpUrl, SecretStr, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # LinkedIn OAuth Settings
    load_dotenv()
    LINKEDIN_CLIENT_ID: SecretStr = os.getenv("LINKEDIN_CLIENT_ID")
    LINKEDIN_CLIENT_SECRET: SecretStr = os.getenv("LINKEDIN_CLIENT_SECRET")
    LINKEDIN_REDIRECT_URI: HttpUrl = os.getenv("LINKEDIN_REDIRECT_URI")

    # API Endpoints
    LINKEDIN_AUTH_URL: HttpUrl = Field(
        default="https://www.linkedin.com/oauth/v2/authorization",
        description="LinkedIn OAuth authorization endpoint"
    )
    LINKEDIN_TOKEN_URL: HttpUrl = Field(
        default="https://www.linkedin.com/oauth/v2/accessToken",
        description="LinkedIn OAuth token endpoint"
    )
    LINKEDIN_USERINFO_URL: HttpUrl = Field(
        default="https://api.linkedin.com/v2/userinfo",
        description="LinkedIn user info endpoint"
    )
    LINKEDIN_POST_URL: HttpUrl = Field(
        default="https://api.linkedin.com/v2/ugcPosts",
        description="LinkedIn posts endpoint"
    )
    LINKEDIN_ASSET_REGISTER_URL: HttpUrl = Field(
        default="https://api.linkedin.com/v2/assets?action=registerUpload",
        description="LinkedIn asset registration endpoint"
    )

    # OAuth Scopes
    LINKEDIN_SCOPES: list[str] = [
        "openid",  # For authentication
        "profile",  # Basic profile access
        "email",  # Email address access
        "w_member_social"  # Required for posting
    ]

    # API Version Headers
    LINKEDIN_VERSION: str = "202210"  # LinkedIn API version
    RESTLI_PROTOCOL_VERSION: str = "2.0.0"  # Rest.li protocol version

    # Token Storage Settings
    TOKEN_STORAGE_PATH: str = os.path.join("linkedin_mcp", "tokens")

    # Logging Configuration
    LOG_LEVEL: str = "INFO"

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True
        validate_default = True
        extra = "forbid"

    @property
    def formatted_scopes(self) -> str:
        """Get properly formatted scope string."""
        return " ".join(self.LINKEDIN_SCOPES)


# Initialize settings
settings = Settings()

# Validate required settings
if not settings.LINKEDIN_CLIENT_ID:
    raise ValueError("LINKEDIN_CLIENT_ID must be set")
if not settings.LINKEDIN_CLIENT_SECRET:
    raise ValueError("LINKEDIN_CLIENT_SECRET must be set")
if not settings.LINKEDIN_REDIRECT_URI:
    raise ValueError("LINKEDIN_REDIRECT_URI must be set")
