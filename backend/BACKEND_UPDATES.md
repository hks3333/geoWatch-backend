# Backend Updates for Sentinel-2 Integration

## Overview
The backend has been updated to handle the new Sentinel-2 analysis workflow with comprehensive metrics, multiple image URLs, and cloud masking information.

---

## Files Modified

### 1. `app/routes/callbacks.py`
**Changes:**
- Added `ImageUrls` model with 5 image URLs (baseline, current, computed masks, difference)
- Added `AnalysisMetrics` model with 13 detailed metrics including cloud coverage
- Updated `AnalysisCompletionPayload` to include new fields
- Enhanced callback handler to store all new data structures
- Maintained backward compatibility by populating old fields (`change_percentage`, `generated_map_url`)

**New Fields Stored:**
```python
{
    "image_urls": {
        "baseline_image": "...",
        "current_image": "...",
        "baseline_computed": "...",
        "current_computed": "...",
        "difference_image": "..."
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
    "bounds": [76.95, 9.82, 77.10, 9.97],
    "baseline_date": "2024-10-15",
    "current_date": "2024-11-10",
    "analysis_type": "forest",
    "change_percentage": -11.07,  // Backward compatibility
    "generated_map_url": "..."     // Backward compatibility
}
```

### 2. `app/models/analysis_result.py`
**Changes:**
- Replaced old `AnalysisStatistics` and `AnalysisImages` models
- Added new `ImageUrls` model matching worker structure
- Added new `AnalysisMetrics` model with comprehensive metrics
- Updated `AnalysisResultInDB` to include:
  - `image_urls`: All 5 GeoTIFF URLs
  - `metrics`: Detailed analysis metrics
  - `bounds`: Bounding box for Leaflet
  - `baseline_date`, `current_date`, `analysis_type`: Top-level for easy querying
  - Backward compatibility fields maintained

**Removed:**
- Old `AnalysisStatistics` model (replaced by `AnalysisMetrics`)
- Old `AnalysisImages` model (replaced by `ImageUrls`)
- Unused fields: `change_detected`, `confidence`, `report_text`

---

## Database Schema

### Firestore `analysis_results` Collection
Each document now has this structure:

```javascript
{
  result_id: "US7Db52lIJgvhbre6JkS",
  area_id: "LNQTQPXrdkp4RmV399Ts",
  area_type: "forest",
  timestamp: Timestamp,
  processing_status: "completed",
  
  // New: All image URLs (Cloud-Optimized GeoTIFFs)
  image_urls: {
    baseline_image: "https://storage.googleapis.com/.../2024-10-15_sentinel.tif",
    current_image: "https://storage.googleapis.com/.../2024-11-10_sentinel.tif",
    baseline_computed: "https://storage.googleapis.com/.../2024-10-15_forest.tif",
    current_computed: "https://storage.googleapis.com/.../2024-11-10_forest.tif",
    difference_image: "https://storage.googleapis.com/.../result_456_diff.tif"
  },
  
  // New: Comprehensive metrics
  metrics: {
    analysis_type: "forest",
    baseline_date: "2024-10-15",
    current_date: "2024-11-10",
    baseline_cloud_coverage: 12.5,
    current_cloud_coverage: 8.3,
    valid_pixels_percentage: 85.7,
    loss_hectares: 45.2,
    gain_hectares: 12.8,
    stable_hectares: 234.5,
    total_hectares: 292.5,
    loss_percentage: 15.45,
    gain_percentage: 4.38,
    net_change_percentage: -11.07
  },
  
  // New: Bounds for Leaflet
  bounds: [76.95, 9.82, 77.10, 9.97],  // [west, south, east, north]
  
  // Top-level for easy querying
  baseline_date: "2024-10-15",
  current_date: "2024-11-10",
  analysis_type: "forest",
  
  // Backward compatibility
  change_percentage: -11.07,
  generated_map_url: "https://storage.googleapis.com/.../result_456_diff.tif"
}
```

---

## API Responses

### GET `/monitoring-areas/{area_id}/results`
Now returns:

```json
{
  "results": [
    {
      "result_id": "US7Db52lIJgvhbre6JkS",
      "area_id": "LNQTQPXrdkp4RmV399Ts",
      "area_type": "forest",
      "timestamp": "2025-11-10T01:25:19.463Z",
      "processing_status": "completed",
      "image_urls": {
        "baseline_image": "https://...",
        "current_image": "https://...",
        "baseline_computed": "https://...",
        "current_computed": "https://...",
        "difference_image": "https://..."
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
      "bounds": [76.95, 9.82, 77.10, 9.97],
      "baseline_date": "2024-10-15",
      "current_date": "2024-11-10",
      "analysis_type": "forest",
      "change_percentage": -11.07,
      "generated_map_url": "https://..."
    }
  ],
  "analysis_in_progress": false
}
```

---

## Backward Compatibility

The following fields are maintained for backward compatibility:
- `change_percentage`: Populated from `metrics.net_change_percentage`
- `generated_map_url`: Populated from `image_urls.difference_image`

This ensures existing frontend code continues to work while new features can use the richer data structure.

---

## No Breaking Changes

✅ All existing API endpoints remain unchanged
✅ All existing response structures are maintained
✅ New fields are added as optional
✅ Worker client requires no changes
✅ Firestore service requires no changes

---

## Testing

After deployment, verify:

1. **Callback Processing**
   ```bash
   # Check Firestore after analysis completes
   # Verify all new fields are populated
   ```

2. **API Response**
   ```bash
   curl http://localhost:8000/monitoring-areas/{area_id}/results
   # Verify response includes image_urls, metrics, bounds
   ```

3. **Backward Compatibility**
   ```bash
   # Verify old fields still present
   # change_percentage and generated_map_url should be populated
   ```

---

## Next Steps for Frontend

1. **Update to use new structure:**
   - Access all 5 image URLs from `image_urls`
   - Display comprehensive metrics from `metrics`
   - Use `bounds` for Leaflet map positioning

2. **Display cloud coverage:**
   - Show `metrics.baseline_cloud_coverage` and `metrics.current_cloud_coverage`
   - Show `metrics.valid_pixels_percentage` to indicate analysis quality

3. **Timeline view:**
   - Use `baseline_date` and `current_date` for timeline
   - Query Firestore by date ranges

4. **Comparison feature:**
   - Fetch all results for an area
   - Let users select any two dates
   - Display corresponding images from `image_urls`

---

## Summary

✅ Backend fully updated to handle Sentinel-2 workflow
✅ All new data structures stored in Firestore
✅ Backward compatibility maintained
✅ No breaking changes to existing APIs
✅ Ready for frontend integration
