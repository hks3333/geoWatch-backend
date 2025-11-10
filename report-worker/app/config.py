"""
Configuration settings for the Report Generation Worker.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google Cloud
    GCP_PROJECT_ID: str
    
    # Gemini API
    GEMINI_API_KEY: str
    
    # Backend
    BACKEND_URL: str = "http://localhost:8000"
    
    # Service defaults (overridden in Cloud Run by env vars)
    PORT: int = 8080
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
