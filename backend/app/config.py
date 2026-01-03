"""
Application configuration using Pydantic Settings.

All environment variables are accessed through this config object.
Never use os.getenv() directly in business logic.
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # AIDP Configuration
    AIDP_API_URL: str = Field(
        default="https://api.aidp.store",
        description="AIDP API base URL",
    )
    AIDP_API_KEY: str = Field(
        default="your_api_key_here",
        description="AIDP API authentication key",
    )
    AIDP_NETWORK_ID: str = Field(
        default="mainnet",
        description="AIDP network identifier",
    )

    # Application Configuration
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "https://proofrender.vercel.app"],
        description="CORS allowed origins",
    )
    MAX_UPLOAD_SIZE: int = Field(
        default=10485760,
        description="Maximum file upload size in bytes (10MB)",
    )
    RATE_LIMIT_REQUESTS: int = Field(
        default=5,
        description="Number of requests allowed per window",
    )
    RATE_LIMIT_WINDOW: int = Field(
        default=3600,
        description="Rate limit time window in seconds",
    )

    # Storage Configuration
    STORAGE_PATH: str = Field(
        default="/app/storage",
        description="Path for file storage",
    )
    FILE_TTL_HOURS: int = Field(
        default=24,
        description="File time-to-live in hours",
    )

    # Blender Configuration
    BLENDER_BINARY: str = Field(
        default="/usr/bin/blender",
        description="Path to Blender executable",
    )
    RENDER_RESOLUTION: str = Field(
        default="1024x1024",
        description="Render output resolution",
    )
    RENDER_SAMPLES: int = Field(
        default=128,
        description="Cycles render samples",
    )
    RENDER_TIMEOUT: int = Field(
        default=300,
        description="Maximum render time in seconds",
    )


# Global settings instance
settings = Settings()
