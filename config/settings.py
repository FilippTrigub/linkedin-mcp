"""MCP LinkedIn server configuration."""
import os

from dotenv import load_dotenv
from pydantic import HttpUrl, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # LinkedIn OIDC Settings
    load_dotenv()
    LINKEDIN_CLIENT_ID: SecretStr = os.getenv("LINKEDIN_CLIENT_ID")
    LINKEDIN_CLIENT_SECRET: SecretStr = os.getenv("LINKEDIN_CLIENT_SECRET")
    LINKEDIN_REDIRECT_URI: HttpUrl = os.getenv("LINKEDIN_REDIRECT_URI")
    
    # API Endpoints
    LINKEDIN_AUTH_URL: HttpUrl = HttpUrl("https://www.linkedin.com/oauth/v2/authorization")
    LINKEDIN_TOKEN_URL: HttpUrl = HttpUrl("https://www.linkedin.com/oauth/v2/accessToken")
    LINKEDIN_USERINFO_URL: HttpUrl = HttpUrl("https://api.linkedin.com/v2/userinfo")
    LINKEDIN_POST_URL: HttpUrl = HttpUrl("https://api.linkedin.com/v2/ugcPosts")
    
    # API Version Headers
    LINKEDIN_VERSION: str = "202210"
    RESTLI_PROTOCOL_VERSION: str = "2.0.0"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True

settings = Settings()