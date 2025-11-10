# GeoWatch Report Generation Worker

AI-powered report generation service using Google Gemini to create comprehensive environmental analysis reports.

## Features

- **Automated Report Generation**: Creates detailed analysis reports using Gemini AI
- **Historical Trend Analysis**: Compares current state with first baseline and tracks changes over time
- **Data Quality Assessment**: Evaluates cloud coverage, valid pixels, and reliability
- **Comprehensive Insights**: Includes loss/gain analysis, environmental context, and recommendations
- **Firestore Integration**: Stores generated reports for easy retrieval
- **Backend Callbacks**: Notifies backend when reports are complete

## Architecture

```
Backend (Analysis Complete) 
    ↓
Report Worker (Gemini AI)
    ↓
Firestore (Store Report)
    ↓
Backend (Callback)
```

## Setup

### 1. Install Dependencies

```bash
cd report-worker
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```env
GCP_PROJECT_ID=your-project-id
GEMINI_API_KEY=your-gemini-api-key
BACKEND_URL=http://localhost:8000
PORT=8002
```

### 3. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to `.env` file

### 4. Run the Service

```bash
python main.py
```

Service will be available at `http://localhost:8002`

## API Endpoints

### Generate Report

**POST** `/generate-report`

Generates a comprehensive analysis report.

**Request Body:**
```json
{
  "area": {
    "area_id": "abc123",
    "name": "Amazon Rainforest Sector A",
    "type": "forest",
    "created_at": "2025-01-01T00:00:00Z",
    "total_analyses": 5
  },
  "latest_result": {
    "result_id": "result_123",
    "timestamp": "2025-11-10T00:00:00Z",
    "processing_status": "completed",
    "metrics": {
      "analysis_type": "forest",
      "baseline_date": "2025-10-10",
      "current_date": "2025-11-10",
      "baseline_cloud_coverage": 5.2,
      "current_cloud_coverage": 8.1,
      "valid_pixels_percentage": 95.5,
      "loss_hectares": 12.5,
      "gain_hectares": 3.2,
      "stable_hectares": 484.3,
      "total_hectares": 500.0,
      "loss_percentage": 2.5,
      "gain_percentage": 0.64,
      "net_change_percentage": -1.86
    }
  },
  "historical_results": []
}
```

**Response:**
```json
{
  "report_id": "report_abc123",
  "area_id": "abc123",
  "generated_at": "2025-11-10T10:00:00Z",
  "summary": "Brief executive summary...",
  "key_findings": [
    "Finding 1: Forest loss detected at 2.5%",
    "Finding 2: High data quality with 95.5% valid pixels"
  ],
  "recommendations": [
    "Recommendation 1: Continue monitoring",
    "Recommendation 2: Investigate loss areas"
  ],
  "report_markdown": "# Full Report\n\n..."
}
```

### Get Report

**GET** `/reports/{report_id}`

Retrieves a previously generated report.

### Get Area Reports

**GET** `/reports/area/{area_id}?limit=10`

Gets all reports for a monitoring area.

## Report Structure

Generated reports include:

1. **Executive Summary**: Brief overview of current state
2. **Data Quality Assessment**: 
   - Cloud coverage analysis
   - Valid pixel percentage
   - Reliability assessment
3. **Current Analysis Results**:
   - Loss, gain, and stable areas
   - Percentage and hectare values
4. **Long-term Trends**:
   - Comparison to first baseline
   - Pattern identification
   - Cumulative changes
5. **Environmental Context**:
   - Interpretation of changes
   - Potential causes
   - Severity assessment
6. **Recommendations**:
   - Immediate actions
   - Long-term strategy

## Firestore Collections

### `analysis_reports`

Stores generated reports:

```javascript
{
  report_id: "report_abc123",
  area_id: "abc123",
  result_id: "result_123",
  generated_at: Timestamp,
  summary: "Executive summary...",
  key_findings: ["Finding 1", "Finding 2"],
  recommendations: ["Rec 1", "Rec 2"],
  report_markdown: "# Full Report...",
  status: "completed"
}
```

## Integration with Backend

The backend automatically triggers report generation after successful analysis:

1. Analysis Worker completes analysis
2. Backend receives callback
3. Backend calls Report Worker with area + historical data
4. Report Worker generates report using Gemini
5. Report Worker saves to Firestore
6. Report Worker sends callback to Backend
7. Backend updates analysis result with report_id

## Development

### Testing Locally

```bash
# Start the service
python main.py

# Test health check
curl http://localhost:8002/health

# Test report generation (use actual data)
curl -X POST http://localhost:8002/generate-report \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

### Logs

The service logs:
- Report generation requests
- Gemini API calls
- Firestore operations
- Callback status

## Performance

- **Generation Time**: ~10-30 seconds per report
- **Gemini Model**: gemini-1.5-flash (fast, cost-effective)
- **Timeout**: 120 seconds for backend calls
- **Concurrent Reports**: Supports multiple simultaneous generations

## Error Handling

- Failed reports trigger error callbacks to backend
- Gemini API errors are logged and reported
- Firestore failures don't prevent report generation
- Callback failures are logged but don't fail the request

## Cost Considerations

Gemini API pricing (as of 2024):
- **gemini-1.5-flash**: $0.35 per 1M input tokens, $1.05 per 1M output tokens
- Average report: ~2,000 input tokens, ~1,500 output tokens
- **Cost per report**: ~$0.002 (very affordable)

## Future Enhancements

- [ ] PDF export
- [ ] Email delivery
- [ ] Scheduled report generation
- [ ] Custom report templates
- [ ] Multi-language support
- [ ] Chart/graph generation
