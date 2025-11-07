"""
This module handles the application's configuration, loading environment variables
using Pydantic's BaseSettings for type-safe access.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    """

    GCP_PROJECT_ID: str
    ANALYSIS_WORKER_URL: str
    BACKEND_ENV: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
