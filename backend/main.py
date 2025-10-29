"""
This is the main entry point for the GeoWatch backend FastAPI application.
It initializes the FastAPI app, includes API routers, and configures middleware.
"""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.routes import health, monitoring_areas, callbacks

app = FastAPI(
    title="GeoWatch Backend API",
    description="API for managing satellite monitoring areas and analysis results.",
    version="0.1.0",
)

# Configure CORS middleware
# In a production environment, you should restrict origins to your frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include API routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(monitoring_areas.router, prefix="/api", tags=["Monitoring Areas"])
app.include_router(callbacks.router, prefix="/api", tags=["Callbacks"])


@app.on_event("startup")
async def startup_event():
    """
    Handles application startup events.
    """
    print("GeoWatch Backend API starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Handles application shutdown events.
    """
    print("GeoWatch Backend API shutting down...")
