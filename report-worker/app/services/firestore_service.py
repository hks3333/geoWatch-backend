"""
Service for storing generated reports in Firestore.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from google.cloud import firestore

logger = logging.getLogger(__name__)


class FirestoreService:
    """Handle Firestore operations for report storage."""
    
    def __init__(self, project_id: str):
        """Initialize Firestore client."""
        self.db = firestore.AsyncClient(project=project_id)
        self.reports_ref = self.db.collection("analysis_reports")
        logger.info(f"Firestore client initialized for project: {project_id}")
    
    async def save_report(
        self,
        report_id: str,
        area_id: str,
        result_id: str,
        report_data: Dict[str, Any]
    ) -> str:
        """
        Save generated report to Firestore.
        
        Args:
            report_id: Unique report identifier
            area_id: Associated monitoring area ID
            result_id: Associated analysis result ID
            report_data: Report content and metadata
            
        Returns:
            Firestore document ID
        """
        doc_data = {
            "report_id": report_id,
            "area_id": area_id,
            "result_id": result_id,
            "generated_at": datetime.now(timezone.utc),
            "summary": report_data.get("summary", ""),
            "key_findings": report_data.get("key_findings", []),
            "recommendations": report_data.get("recommendations", []),
            "report_markdown": report_data.get("report_markdown", ""),
            "status": "completed"
        }
        
        doc_ref = self.reports_ref.document(report_id)
        await doc_ref.set(doc_data)
        
        logger.info(f"Report {report_id} saved to Firestore")
        return report_id
    
    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a report by ID."""
        doc_ref = self.reports_ref.document(report_id)
        doc = await doc_ref.get()
        
        if doc.exists:
            return doc.to_dict()
        return None
    
    async def get_reports_for_area(self, area_id: str, limit: int = 10) -> list:
        """Get all reports for a monitoring area."""
        query = (
            self.reports_ref
            .where("area_id", "==", area_id)
            .order_by("generated_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        
        reports = []
        async for doc in query.stream():
            report_data = doc.to_dict()
            reports.append(report_data)
        
        return reports
