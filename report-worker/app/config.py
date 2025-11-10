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
    
    # Service
    PORT: int = 8002
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
