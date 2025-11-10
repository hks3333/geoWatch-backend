"""
This module handles the application's configuration, loading environment variables
using Pydantic's BaseSettings for type-safe access.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    
    For production, ensure these environment variables are set:
    - GCP_PROJECT_ID: Your GCP project ID
    - BACKEND_ENV: Set to "production" for production mode
    - ANALYSIS_WORKER_URL: URL of the Analysis Worker service
    - REPORT_WORKER_URL: URL of the Report Worker service (optional, defaults to localhost)
    """

    GCP_PROJECT_ID: str = "cloudrun-476105"
    BACKEND_ENV: str = "local"  # "local" or "production"
    ANALYSIS_WORKER_URL: str = "http://localhost:8001"  # Local default
    REPORT_WORKER_URL: str = "http://localhost:8002"  # Local default

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @field_validator('BACKEND_ENV')
    @classmethod
    def validate_backend_env(cls, v: str) -> str:
        allowed = {"local", "production"}
        value = v.lower().strip()
        if value not in allowed:
            raise ValueError(f"BACKEND_ENV must be one of {allowed}")
        return value

    @field_validator('ANALYSIS_WORKER_URL', 'REPORT_WORKER_URL')
    @classmethod
    def validate_urls(cls, v):
        """Ensure URLs are properly formatted."""
        if not v:
            raise ValueError("Worker URLs cannot be empty")
        # Remove trailing slashes for consistency
        return v.rstrip('/')


settings = Settings()
