"""
API routes for accessing analysis reports.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import httpx

from app.config import settings
from app.services.firestore_service import FirestoreService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_firestore_service() -> FirestoreService:
    """Dependency to get Firestore service instance."""
    return FirestoreService(project_id=settings.GCP_PROJECT_ID)


class ReportSummary(BaseModel):
    """Summary of a report for listing."""
    report_id: str
    area_id: str
    result_id: str
    generated_at: str
    summary: str
    status: str


class ReportDetail(BaseModel):
    """Full report details."""
    report_id: str
    area_id: str
    result_id: str
    generated_at: str
    summary: str
    key_findings: List[str]
    recommendations: List[str]
    report_markdown: str
    status: str


@router.get("/reports/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: str,
    db: FirestoreService = Depends(get_firestore_service)
):
    """
    Get a specific report by ID.
    
    Args:
        report_id: Unique report identifier
        
    Returns:
        Full report details including markdown content
    """
    try:
        # Try to get from report worker first
        report_worker_url = settings.REPORT_WORKER_URL
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{report_worker_url}/reports/{report_id}")
                
                if response.status_code == 200:
                    report_data = response.json()
                    
                    # Convert timestamp if needed
                    if "generated_at" in report_data and hasattr(report_data["generated_at"], "isoformat"):
                        report_data["generated_at"] = report_data["generated_at"].isoformat()
                    
                    return ReportDetail(**report_data)
        except Exception as e:
            logger.warning(f"Failed to fetch from report worker: {e}, trying Firestore")
        
        # Fallback to direct Firestore query
        reports_ref = db.db.collection("analysis_reports")
        doc = await reports_ref.document(report_id).get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        report_data = doc.to_dict()
        
        # Convert Firestore timestamp
        if "generated_at" in report_data:
            if hasattr(report_data["generated_at"], "isoformat"):
                report_data["generated_at"] = report_data["generated_at"].isoformat()
            else:
                report_data["generated_at"] = str(report_data["generated_at"])
        
        return ReportDetail(**report_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve report {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report: {str(e)}"
        )


@router.get("/areas/{area_id}/reports", response_model=List[ReportSummary])
async def get_area_reports(
    area_id: str,
    limit: int = 10,
    db: FirestoreService = Depends(get_firestore_service)
):
    """
    Get all reports for a monitoring area.
    
    Args:
        area_id: Monitoring area ID
        limit: Maximum number of reports to return
        
    Returns:
        List of report summaries
    """
    try:
        # Query Firestore directly for better performance
        reports_ref = db.db.collection("analysis_reports")
        query = (
            reports_ref
            .where("area_id", "==", area_id)
            .order_by("generated_at", direction="DESCENDING")
            .limit(limit)
        )
        
        reports = []
        async for doc in query.stream():
            report_data = doc.to_dict()
            
            # Convert timestamp
            if "generated_at" in report_data:
                if hasattr(report_data["generated_at"], "isoformat"):
                    report_data["generated_at"] = report_data["generated_at"].isoformat()
                else:
                    report_data["generated_at"] = str(report_data["generated_at"])
            
            reports.append(ReportSummary(
                report_id=report_data["report_id"],
                area_id=report_data["area_id"],
                result_id=report_data["result_id"],
                generated_at=report_data["generated_at"],
                summary=report_data.get("summary", ""),
                status=report_data.get("status", "completed")
            ))
        
        return reports
        
    except Exception as e:
        logger.error(f"Failed to retrieve reports for area {area_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reports: {str(e)}"
        )


@router.get("/results/{result_id}/report")
async def get_result_report(
    result_id: str,
    db: FirestoreService = Depends(get_firestore_service)
):
    """
    Get the report associated with an analysis result.
    
    Args:
        result_id: Analysis result ID
        
    Returns:
        Report details or 404 if no report exists
    """
    try:
        # Query for report by result_id
        reports_ref = db.db.collection("analysis_reports")
        query = reports_ref.where("result_id", "==", result_id).limit(1)
        
        report_data = None
        async for doc in query.stream():
            report_data = doc.to_dict()
            break
        
        if not report_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No report found for result {result_id}"
            )
        
        # Convert timestamp
        if "generated_at" in report_data:
            if hasattr(report_data["generated_at"], "isoformat"):
                report_data["generated_at"] = report_data["generated_at"].isoformat()
            else:
                report_data["generated_at"] = str(report_data["generated_at"])
        
        return ReportDetail(**report_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve report for result {result_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report: {str(e)}"
        )
