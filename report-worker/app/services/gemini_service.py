"""
Service for generating reports using Google Gemini AI.
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
import json

import google.generativeai as genai

from app.config import settings
from app.models import ReportGenerationRequest, AnalysisResult

logger = logging.getLogger(__name__)


class GeminiReportGenerator:
    """Generate detailed analysis reports using Gemini AI."""
    
    def __init__(self):
        """Initialize Gemini API."""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def generate_report(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """
        Generate a comprehensive analysis report.
        
        Args:
            request: Report generation request with area and analysis data
            
        Returns:
            Dict with report content, summary, findings, and recommendations
        """
        logger.info(f"Generating report for area {request.area.area_id}")
        
        # Prepare context for Gemini
        context = self._prepare_context(request)
        
        # Generate report using Gemini
        prompt = self._build_prompt(context)
        
        try:
            response = self.model.generate_content(prompt)
            report_text = response.text
            
            # Parse structured output
            parsed = self._parse_report(report_text)
            
            logger.info(f"Successfully generated report for area {request.area.area_id}")
            return parsed
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            raise
    
    def _prepare_context(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare analysis context for report generation."""
        area = request.area
        latest = request.latest_result
        historical = request.historical_results
        
        # Calculate trends from historical data
        trend_data = self._calculate_trends(historical + [latest])
        
        # Find first baseline for comparison
        first_baseline = None
        if historical:
            completed = [r for r in historical if r.processing_status == 'completed' and r.metrics]
            if completed:
                first_baseline = completed[0]
        
        context = {
            "area": {
                "name": area.name,
                "type": area.type,
                "created_at": area.created_at,
                "total_analyses": area.total_analyses
            },
            "latest_analysis": {
                "date": latest.timestamp,
                "status": latest.processing_status,
                "metrics": latest.metrics.model_dump() if latest.metrics else None
            },
            "first_baseline": {
                "date": first_baseline.timestamp,
                "metrics": first_baseline.metrics.model_dump()
            } if first_baseline and first_baseline.metrics else None,
            "historical_count": len(historical),
            "trends": trend_data
        }
        
        return context
    
    def _calculate_trends(self, results: List[AnalysisResult]) -> Dict[str, Any]:
        """Calculate trends from historical analysis results."""
        completed = [r for r in results if r.processing_status == 'completed' and r.metrics]
        
        if len(completed) < 2:
            return {
                "available": False,
                "message": "Insufficient data for trend analysis"
            }
        
        # Extract time series data
        dates = [r.metrics.current_date for r in completed]
        losses = [r.metrics.loss_percentage for r in completed]
        gains = [r.metrics.gain_percentage for r in completed]
        net_changes = [r.metrics.net_change_percentage for r in completed]
        cloud_coverage = [r.metrics.current_cloud_coverage for r in completed]
        
        return {
            "available": True,
            "period": {
                "start": dates[0],
                "end": dates[-1],
                "analyses_count": len(completed)
            },
            "loss": {
                "values": losses,
                "average": sum(losses) / len(losses),
                "min": min(losses),
                "max": max(losses),
                "trend": "increasing" if losses[-1] > losses[0] else "decreasing"
            },
            "gain": {
                "values": gains,
                "average": sum(gains) / len(gains),
                "min": min(gains),
                "max": max(gains),
                "trend": "increasing" if gains[-1] > gains[0] else "decreasing"
            },
            "net_change": {
                "values": net_changes,
                "average": sum(net_changes) / len(net_changes),
                "cumulative": sum(net_changes)
            },
            "data_quality": {
                "avg_cloud_coverage": sum(cloud_coverage) / len(cloud_coverage),
                "best_quality": min(cloud_coverage),
                "worst_quality": max(cloud_coverage)
            }
        }
    
    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """Build comprehensive prompt for Gemini."""
        area_type = context["area"]["type"]
        area_name = context["area"]["name"]
        
        prompt = f"""You are an expert environmental analyst specializing in satellite imagery analysis and {area_type} monitoring. Generate a comprehensive, professional analysis report based on the following data.

MONITORING AREA INFORMATION:
{json.dumps(context["area"], indent=2)}

LATEST ANALYSIS:
{json.dumps(context["latest_analysis"], indent=2)}

FIRST BASELINE (for long-term comparison):
{json.dumps(context["first_baseline"], indent=2) if context["first_baseline"] else "Not available"}

HISTORICAL TRENDS:
{json.dumps(context["trends"], indent=2)}

Generate a detailed report in the following JSON format:
{{
    "summary": "A 2-3 sentence executive summary of the current state and key findings",
    "key_findings": [
        "Finding 1: Specific, data-backed observation",
        "Finding 2: Another important observation",
        "Finding 3-5: Additional findings"
    ],
    "recommendations": [
        "Recommendation 1: Actionable suggestion based on findings",
        "Recommendation 2: Another recommendation",
        "Recommendation 3-4: Additional recommendations"
    ],
    "report_markdown": "# Full detailed markdown report here"
}}

The full markdown report should include:

1. **Executive Summary**: Brief overview of current state
2. **Data Quality Assessment**: 
   - Cloud coverage analysis
   - Valid pixel percentage
   - Reliability assessment
   - Data completeness
3. **Current Analysis Results**:
   - Detailed breakdown of loss, gain, and stable areas
   - Percentage and hectare values
   - Comparison to baseline period
4. **Long-term Trends** (if historical data available):
   - Compare current state to first baseline
   - Identify patterns and trends
   - Calculate cumulative changes
   - Assess rate of change
5. **Environmental Context**:
   - Interpret what the changes mean for {area_type} health
   - Discuss potential causes
   - Assess severity and urgency
6. **Data Reliability**:
   - Confidence level in the analysis
   - Factors affecting accuracy
   - Limitations and caveats
7. **Recommendations**:
   - Immediate actions needed
   - Long-term monitoring strategy
   - Areas requiring attention

Use professional, scientific language. Include specific numbers and percentages. Be objective and data-driven. Format the markdown with proper headers, bullet points, and emphasis where appropriate.

Respond ONLY with valid JSON matching the format above. Do not include any text outside the JSON structure."""

        return prompt
    
    def _parse_report(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response into structured format."""
        try:
            text = response_text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            
            if text.endswith("```"):
                text = text[:-3]
            
            text = text.strip()
            
            # Try to find JSON object if wrapped in text
            if not text.startswith("{"):
                # Look for JSON object in the text
                start_idx = text.find("{")
                end_idx = text.rfind("}") + 1
                if start_idx != -1 and end_idx > start_idx:
                    text = text[start_idx:end_idx]
            
            # Use json.JSONDecoder with strict=False to handle some formatting issues
            # But first, try direct parsing
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                # If that fails, try replacing literal newlines with escaped newlines
                # This handles cases where Gemini puts actual newlines in string values
                text_fixed = text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                parsed = json.loads(text_fixed)
            
            # Validate required fields
            required = ["summary", "key_findings", "recommendations", "report_markdown"]
            for field in required:
                if field not in parsed:
                    logger.warning(f"Missing field in response: {field}")
                    if field == "key_findings":
                        parsed[field] = []
                    elif field == "recommendations":
                        parsed[field] = []
                    elif field == "summary":
                        parsed[field] = "Report generated"
                    elif field == "report_markdown":
                        parsed[field] = ""
            
            # Ensure fields are correct types
            if not isinstance(parsed.get("key_findings"), list):
                parsed["key_findings"] = [str(parsed.get("key_findings", ""))]
            if not isinstance(parsed.get("recommendations"), list):
                parsed["recommendations"] = [str(parsed.get("recommendations", ""))]
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            raise ValueError(f"Could not parse report response: {e}")
