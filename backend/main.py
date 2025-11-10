"""
This is the main entry point for the GeoWatch backend FastAPI application.
It initializes the FastAPI app, includes API routers, and configures middleware.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import callbacks, health, monitoring_areas, reports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Determine environment
IS_PRODUCTION = settings.BACKEND_ENV == "production"

# Configure CORS based on environment
if IS_PRODUCTION:
    # Production: Restrict to frontend URL only
    allowed_origins = [
        "https://geowatch-frontend.run.app",
        "https://yourdomain.com",  # Update with your custom domain
    ]
    logger.info("🚀 Production mode: CORS restricted to %s", allowed_origins)
else:
    # Local development: Allow all origins
    allowed_origins = ["*"]
    logger.info("🔧 Local mode: CORS allows all origins")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("=" * 60)
    logger.info("GeoWatch Backend API starting up...")
    logger.info("Environment: %s", "PRODUCTION" if IS_PRODUCTION else "LOCAL")
    logger.info("Analysis Worker URL: %s", settings.ANALYSIS_WORKER_URL)
    logger.info("Report Worker URL: %s", settings.REPORT_WORKER_URL)
    logger.info("GCP Project: %s", settings.GCP_PROJECT_ID)
    logger.info("=" * 60)
    
    # Initialize worker client
    await initialize_worker_client()
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("GeoWatch Backend API shutting down...")
    await close_worker_client()
    logger.info("=" * 60)

app = FastAPI(
    title="GeoWatch Backend API",
    description="API for managing satellite monitoring areas and analysis results.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(monitoring_areas.router, prefix="/api", tags=["Monitoring Areas"])
app.include_router(callbacks.router, prefix="/api/callbacks", tags=["Callbacks"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])


from typing import Optional
from app.services.worker_client import WorkerClient

worker_client: Optional[WorkerClient] = None

# Initialize worker client after app startup
async def initialize_worker_client():
    """Initialize the worker client for communicating with Analysis Worker."""
    global worker_client
    try:
        worker_client = WorkerClient(worker_url=settings.ANALYSIS_WORKER_URL)
        logger.info("✅ Worker client initialized successfully")
        return True
    except Exception as e:
        logger.error("❌ Failed to initialize worker client: %s", e)
        return False

async def close_worker_client():
    """Close the worker client connection."""
    global worker_client
    if worker_client:
        try:
            await worker_client.close()
            logger.info("✅ Worker client closed successfully")
        except Exception as e:
            logger.error("❌ Error closing worker client: %s", e)
