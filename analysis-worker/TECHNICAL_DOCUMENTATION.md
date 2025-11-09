# GeoWatch Analysis Worker - Technical Documentation

## Overview
The Analysis Worker has been completely revamped to use **Sentinel-2 satellite imagery** instead of Google Dynamic World. It performs change detection for **forest** and **water** monitoring with advanced cloud masking.

---

## Architecture Changes

### Previous System (Dynamic World)
- Used pre-classified Dynamic World data
- Simple mode composite
- PNG visualization only
- Limited metadata

### New System (Sentinel-2)
- Raw Sentinel-2 SR Harmonized imagery
- Custom classification using NDVI (forest) and MNDWI (water)
- Cloud masking with SCL band
- Cloud-Optimized GeoTIFF exports
- Comprehensive metadata and metrics

---

## Workflow

### 1. Image Acquisition
**Endpoint**: `POST /analyze`

**Process**:
1. Receives analysis request from backend with:
   - `area_id`: Monitoring area identifier
   - `result_id`: Unique result identifier
   - `polygon`: Area boundary coordinates
   - `type`: Analysis type (`forest` or `water`)
   - `is_baseline`: First analysis flag

2. Fetches **current image**: Latest Sentinel-2 image (last 60 days)
3. Fetches **baseline image**: Image from ~1 month before current (±10 days window)

**Sentinel-2 Bands Used**:
- `B2` (Blue): 490nm
- `B3` (Green): 560nm
- `B4` (Red): 665nm
- `B8` (NIR): 842nm
- `B11` (SWIR): 1610nm
- `SCL` (Scene Classification Layer): Cloud mask

### 2. Cloud Masking
**SCL Values Masked**:
- `3`: Cloud Shadow
- `8`: Cloud Medium Probability
- `9`: Cloud High Probability
- `10`: Cirrus

**Combined Mask**: Only pixels cloud-free in BOTH images are analyzed

**Metrics Calculated**:
- Baseline cloud coverage %
- Current cloud coverage %
- Valid pixels percentage (cloud-free in both)

### 3. Classification

#### Forest Detection (NDVI)
```
NDVI = (NIR - Red) / (NIR + Red) = (B8 - B4) / (B8 + B4)
Threshold: NDVI > 0.4 = Forest
```

#### Water Detection (MNDWI)
```
MNDWI = (Green - SWIR) / (Green + SWIR) = (B3 - B11) / (B3 + B11)
Threshold: MNDWI > 0.3 = Water
```

### 4. Change Detection
**Categories**:
- **Loss**: Classified in baseline, NOT in current
- **Gain**: NOT in baseline, classified in current
- **Stable**: Classified in both

**Metrics**:
- Loss/Gain/Stable in hectares
- Loss/Gain percentages
- Net change percentage

### 5. Image Export
All images exported as **Cloud-Optimized GeoTIFFs (COG)** to GCS:

**Storage Structure**:
```
gs://bucket-name/
  {area_id}/
    images/
      YYYY-MM-DD_sentinel.tif       # RGB composite (B4, B3, B2)
    computed/
      YYYY-MM-DD_forest.tif          # Binary mask (0 or 1)
      YYYY-MM-DD_water.tif           # Binary mask (0 or 1)
    comparisons/
      {result_id}_diff.tif           # RGB visualization (R=Loss, G=Stable, B=Gain)
```

**COG Parameters**:
- **CRS**: EPSG:3857 (Web Mercator) for Leaflet compatibility
- **Resolution**: 10m
- **Format**: GeoTIFF with `cloudOptimized: true`
- **Compression**: Automatic

---

## API Integration

### Backend → Worker Request
**Endpoint**: `POST http://worker-url/analyze`

**Payload**:
```json
{
  "area_id": "area_123",
  "result_id": "result_456",
  "polygon": [
    [76.95, 9.82],
    [77.10, 9.82],
    [77.10, 9.97],
    [76.95, 9.97],
    [76.95, 9.82]
  ],
  "type": "forest",  // or "water"
  "is_baseline": false
}
```

**Response**: `202 Accepted` (immediate)

### Worker → Backend Callback
**Endpoint**: `POST {BACKEND_API_URL}/callbacks/analysis-complete`

**Success Payload**:
```json
{
  "result_id": "result_456",
  "status": "completed",
  "image_urls": {
    "baseline_image": "https://storage.googleapis.com/bucket/area_123/images/2024-10-15_sentinel.tif",
    "current_image": "https://storage.googleapis.com/bucket/area_123/images/2024-11-10_sentinel.tif",
    "baseline_computed": "https://storage.googleapis.com/bucket/area_123/computed/2024-10-15_forest.tif",
    "current_computed": "https://storage.googleapis.com/bucket/area_123/computed/2024-11-10_forest.tif",
    "difference_image": "https://storage.googleapis.com/bucket/area_123/comparisons/result_456_diff.tif"
  },
  "metrics": {
    "analysis_type": "forest",
    "baseline_date": "2024-10-15",
    "current_date": "2024-11-10",
    "baseline_cloud_coverage": 12.5,
    "current_cloud_coverage": 8.3,
    "valid_pixels_percentage": 85.7,
    "loss_hectares": 45.2,
    "gain_hectares": 12.8,
    "stable_hectares": 234.5,
    "total_hectares": 292.5,
    "loss_percentage": 15.45,
    "gain_percentage": 4.38,
    "net_change_percentage": -11.07
  },
  "bounds": [76.95, 9.82, 77.10, 9.97]  // [west, south, east, north]
}
```

**Failure Payload**:
```json
{
  "result_id": "result_456",
  "status": "failed",
  "error_message": "No Sentinel-2 data available for current window"
}
```

---

## Frontend Integration (Leaflet)

### Displaying GeoTIFFs in Leaflet

#### Option 1: Using georaster-layer-for-leaflet
```javascript
import GeoRasterLayer from "georaster-layer-for-leaflet";
import parseGeoraster from "georaster";

// Fetch and parse GeoTIFF
const response = await fetch(imageUrl);
const arrayBuffer = await response.arrayBuffer();
const georaster = await parseGeoraster(arrayBuffer);

// Create layer
const layer = new GeoRasterLayer({
  georaster: georaster,
  opacity: 0.7,
  resolution: 256
});

layer.addTo(map);
```

#### Option 2: Using Leaflet.TileLayer with COG
```javascript
// For COG, you can use a tile server or direct rendering
const layer = L.tileLayer(
  'https://your-tile-server.com/tiles/{z}/{x}/{y}?url=' + encodeURIComponent(imageUrl),
  {
    attribution: 'Sentinel-2',
    maxZoom: 18
  }
);

layer.addTo(map);
```

### Setting Map Bounds
```javascript
const bounds = response.bounds; // [west, south, east, north]
map.fitBounds([
  [bounds[1], bounds[0]], // southwest
  [bounds[3], bounds[2]]  // northeast
]);
```

### Displaying Metrics
```javascript
const metrics = response.metrics;

// Create info panel
const info = L.control({ position: 'topright' });
info.onAdd = function(map) {
  const div = L.DomUtil.create('div', 'info');
  div.innerHTML = `
    <h4>${metrics.analysis_type.toUpperCase()} Change Detection</h4>
    <p><strong>Period:</strong> ${metrics.baseline_date} to ${metrics.current_date}</p>
    <p><strong>Cloud Coverage:</strong> Baseline ${metrics.baseline_cloud_coverage.toFixed(1)}%, Current ${metrics.current_cloud_coverage.toFixed(1)}%</p>
    <p><strong>Valid Pixels:</strong> ${metrics.valid_pixels_percentage.toFixed(1)}%</p>
    <hr>
    <p style="color: red;"><strong>Loss:</strong> ${metrics.loss_hectares.toFixed(2)} ha (${metrics.loss_percentage.toFixed(2)}%)</p>
    <p style="color: blue;"><strong>Gain:</strong> ${metrics.gain_hectares.toFixed(2)} ha (${metrics.gain_percentage.toFixed(2)}%)</p>
    <p style="color: green;"><strong>Stable:</strong> ${metrics.stable_hectares.toFixed(2)} ha</p>
    <p><strong>Net Change:</strong> ${metrics.net_change_percentage.toFixed(2)}%</p>
  `;
  return div;
};
info.addTo(map);
```

### Comparison Feature
For comparing any two images:

1. **Backend stores metadata** in database:
```javascript
{
  area_id: "area_123",
  date: "2024-11-10",
  type: "forest",
  image_url: "gs://bucket/area_123/images/2024-11-10_sentinel.tif",
  computed_url: "gs://bucket/area_123/computed/2024-11-10_forest.tif"
}
```

2. **Frontend fetches available dates**:
```javascript
GET /api/areas/{area_id}/images?type=forest
```

3. **User selects two dates**, frontend requests new analysis:
```javascript
POST /api/areas/{area_id}/compare
{
  "baseline_date": "2024-10-15",
  "current_date": "2024-11-10",
  "type": "forest"
}
```

4. **Backend triggers worker** with specific dates (modify worker to accept optional dates)

---

## Backend Implementation Guide

### 1. Database Schema Updates

#### AnalysisResult Model
```javascript
{
  _id: ObjectId,
  area_id: ObjectId,
  result_id: String,
  status: String, // 'pending', 'completed', 'failed'
  type: String, // 'forest', 'water'
  baseline_date: Date,
  current_date: Date,
  
  // Image URLs
  image_urls: {
    baseline_image: String,
    current_image: String,
    baseline_computed: String,
    current_computed: String,
    difference_image: String
  },
  
  // Metrics
  metrics: {
    baseline_cloud_coverage: Number,
    current_cloud_coverage: Number,
    valid_pixels_percentage: Number,
    loss_hectares: Number,
    gain_hectares: Number,
    stable_hectares: Number,
    total_hectares: Number,
    loss_percentage: Number,
    gain_percentage: Number,
    net_change_percentage: Number
  },
  
  bounds: [Number], // [west, south, east, north]
  
  created_at: Date,
  updated_at: Date
}
```

### 2. API Endpoints

#### Trigger Analysis
```javascript
POST /api/areas/:areaId/analyze

// Request
{
  "type": "forest" // or "water"
}

// Response
{
  "result_id": "result_456",
  "status": "pending"
}

// Implementation
async function triggerAnalysis(req, res) {
  const { areaId } = req.params;
  const { type } = req.body;
  
  const area = await MonitoringArea.findById(areaId);
  const result_id = generateUniqueId();
  
  // Create pending result
  const result = await AnalysisResult.create({
    area_id: areaId,
    result_id,
    status: 'pending',
    type
  });
  
  // Call worker
  await axios.post(`${WORKER_URL}/analyze`, {
    area_id: areaId,
    result_id,
    polygon: area.polygon,
    type,
    is_baseline: area.analysis_count === 0
  });
  
  res.json({ result_id, status: 'pending' });
}
```

#### Callback Handler
```javascript
POST /api/callbacks/analysis-complete

// Implementation
async function handleCallback(req, res) {
  const { result_id, status, image_urls, metrics, bounds, error_message } = req.body;
  
  const update = {
    status,
    updated_at: new Date()
  };
  
  if (status === 'completed') {
    update.image_urls = image_urls;
    update.metrics = metrics;
    update.bounds = bounds;
    update.baseline_date = new Date(metrics.baseline_date);
    update.current_date = new Date(metrics.current_date);
  } else {
    update.error_message = error_message;
  }
  
  await AnalysisResult.findOneAndUpdate(
    { result_id },
    update
  );
  
  // Optionally notify frontend via WebSocket
  io.to(result_id).emit('analysis_complete', update);
  
  res.json({ success: true });
}
```

#### Get Results
```javascript
GET /api/areas/:areaId/results?type=forest&limit=10

// Response
{
  "results": [
    {
      "result_id": "result_456",
      "status": "completed",
      "type": "forest",
      "baseline_date": "2024-10-15",
      "current_date": "2024-11-10",
      "metrics": { ... },
      "image_urls": { ... },
      "bounds": [...]
    }
  ]
}
```

#### Get Available Dates (for comparison)
```javascript
GET /api/areas/:areaId/images?type=forest

// Response
{
  "images": [
    {
      "date": "2024-11-10",
      "image_url": "...",
      "computed_url": "..."
    },
    {
      "date": "2024-10-15",
      "image_url": "...",
      "computed_url": "..."
    }
  ]
}
```

---

## Environment Variables

### Worker (.env)
```bash
GCP_PROJECT_ID=your-project-id
BACKEND_API_URL=https://your-backend.com
BACKEND_ENV=production
GCS_BUCKET_NAME=geowatch-analysis-maps
```

### Backend
```bash
WORKER_URL=https://your-worker.com
```

---

## Deployment

### Worker Deployment (Cloud Run)
```dockerfile
# Already configured in existing Dockerfile
# Ensure service account has:
# - Earth Engine access
# - GCS write permissions
```

### GCS Bucket Setup
```bash
# Create bucket
gsutil mb -p your-project-id gs://geowatch-analysis-maps

# Set CORS for frontend access
cat > cors.json << EOF
[
  {
    "origin": ["https://your-frontend.com"],
    "method": ["GET"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF

gsutil cors set cors.json gs://geowatch-analysis-maps

# Make bucket publicly readable (or use signed URLs)
gsutil iam ch allUsers:objectViewer gs://geowatch-analysis-maps
```

---

## Performance Considerations

### Processing Time
- Image fetch: ~5-10 seconds
- Cloud masking & classification: ~10-20 seconds
- Change detection: ~5-10 seconds
- GeoTIFF export: ~30-60 seconds per image (5 images total)
- **Total**: ~3-5 minutes per analysis

### Optimization Tips
1. **Parallel exports**: Modify storage service to export images in parallel
2. **Caching**: Store computed masks to avoid reprocessing
3. **Smaller ROIs**: Limit polygon size to reduce processing time
4. **Async frontend**: Use WebSockets for real-time updates

---

## Error Handling

### Common Errors

#### No Sentinel-2 Data
```
Error: "No Sentinel-2 data available for current window"
Solution: Expand date range or check if area is covered by Sentinel-2
```

#### High Cloud Coverage
```
Warning: valid_pixels_percentage < 50%
Solution: Display warning to user, suggest retrying later
```

#### Export Timeout
```
Error: "Export timed out after 300s"
Solution: Increase timeout or reduce ROI size
```

---

## Testing

### Manual Test
```bash
# Start worker locally
cd analysis-worker
uvicorn main:app --reload

# Send test request
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "area_id": "test_area",
    "result_id": "test_result",
    "polygon": [[76.95, 9.82], [77.10, 9.82], [77.10, 9.97], [76.95, 9.97], [76.95, 9.82]],
    "type": "forest",
    "is_baseline": true
  }'
```

---

## Monitoring

### Key Metrics to Track
- Analysis success rate
- Average processing time
- Cloud coverage statistics
- GCS storage usage
- Earth Engine quota usage

### Logging
All operations logged with:
- `result_id` for tracing
- Step-by-step progress
- Error details with stack traces

---

## Future Enhancements

1. **Parallel image exports** for faster processing
2. **Custom date selection** for comparisons
3. **Multi-temporal analysis** (>2 images)
4. **Additional indices**: EVI, SAVI, NDBI
5. **Alert system** for significant changes
6. **Historical data caching** to avoid reprocessing

---

## Support

For issues or questions:
- Check logs in Cloud Run console
- Verify Earth Engine authentication
- Ensure GCS permissions are correct
- Test with smaller ROIs first
