"""
Report Generation Worker - Main application entry point.
Generates comprehensive analysis reports using Gemini AI.
"""
import logging
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import ReportGenerationRequest, ReportGenerationResponse
from app.services.gemini_service import GeminiReportGenerator
from app.services.firestore_service import FirestoreService
from app.services.callback_client import CallbackClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
gemini_generator = None
firestore_service = None
callback_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global gemini_generator, firestore_service, callback_client
    
    logger.info("Initializing Report Generation Worker...")
    
    # Initialize services
    gemini_generator = GeminiReportGenerator()
    firestore_service = FirestoreService(project_id=settings.GCP_PROJECT_ID)
    callback_client = CallbackClient()
    
    logger.info("Report Generation Worker ready")
    
    yield
    
    logger.info("Shutting down Report Generation Worker")


app = FastAPI(
    title="GeoWatch Report Generation Worker",
    description="Generates comprehensive analysis reports using Gemini AI",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "report-worker",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/generate-report", response_model=ReportGenerationResponse)
async def generate_report(request: ReportGenerationRequest):
    """
    Generate a comprehensive analysis report.
    
    This endpoint:
    1. Receives area and analysis data
    2. Generates report using Gemini AI
    3. Saves report to Firestore
    4. Sends callback to backend
    5. Returns report content
    """
    report_id = f"report_{uuid.uuid4().hex[:12]}"
    
    logger.info(f"Starting report generation: {report_id}")
    logger.info(f"Area: {request.area.name} ({request.area.area_id})")
    logger.info(f"Latest result: {request.latest_result.result_id}")
    logger.info(f"Historical results: {len(request.historical_results)}")
    
    try:
        # Step 1: Generate report using Gemini
        logger.info(f"Step 1/4: Generating report with Gemini AI")
        report_data = gemini_generator.generate_report(request)
        
        # Step 2: Save to Firestore
        logger.info(f"Step 2/4: Saving report to Firestore")
        await firestore_service.save_report(
            report_id=report_id,
            area_id=request.area.area_id,
            result_id=request.latest_result.result_id,
            report_data=report_data
        )
        
        # Step 3: Send callback to backend
        logger.info(f"Step 3/4: Sending callback to backend")
        callback_success = await callback_client.send_completion_callback(
            report_id=report_id,
            area_id=request.area.area_id,
            result_id=request.latest_result.result_id,
            status="completed",
            summary=report_data.get("summary", "")
        )
        
        if not callback_success:
            logger.warning(f"Callback failed for report {report_id}, but report was generated")
        
        # Step 4: Return response
        logger.info(f"Step 4/4: Report generation complete")
        logger.info(f"Report {report_id} generated successfully")
        
        response = ReportGenerationResponse(
            report_id=report_id,
            area_id=request.area.area_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            report_markdown=report_data["report_markdown"],
            summary=report_data["summary"],
            key_findings=report_data["key_findings"],
            recommendations=report_data["recommendations"]
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to generate report {report_id}: {e}", exc_info=True)
        
        # Send failure callback
        try:
            await callback_client.send_completion_callback(
                report_id=report_id,
                area_id=request.area.area_id,
                result_id=request.latest_result.result_id,
                status="failed",
                error_message=str(e)
            )
        except Exception as callback_error:
            logger.error(f"Failed to send failure callback: {callback_error}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Retrieve a generated report by ID."""
    try:
        report = await firestore_service.get_report(report_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve report {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report: {str(e)}"
        )


@app.get("/reports/area/{area_id}")
async def get_area_reports(area_id: str, limit: int = 10):
    """Get all reports for a monitoring area."""
    try:
        reports = await firestore_service.get_reports_for_area(area_id, limit)
        return {"area_id": area_id, "reports": reports, "count": len(reports)}
        
    except Exception as e:
        logger.error(f"Failed to retrieve reports for area {area_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reports: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True
    )
