"""
This module configures the application settings using Pydantic's BaseSettings.
It loads environment variables from a .env file and validates them, providing
a centralized and type-safe way to manage configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Defines the application's configuration settings, loaded from environment variables.

    Attributes:
        GCP_PROJECT_ID (str): The Google Cloud Project ID.
        BACKEND_API_URL (str): The URL for the backend API, used for callbacks.
    """

    # Load environment variables from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    GCP_PROJECT_ID: str = "your-gcp-project-id"
    BACKEND_API_URL: str = "http://localhost:8000"


# Create a single, reusable instance of the settings
settings = Settings()
