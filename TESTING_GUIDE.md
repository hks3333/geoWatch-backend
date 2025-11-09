# GeoWatch Testing Guide - Part 1

## Prerequisites

### 1. Start Backend
```bash
cd backend
# Activate virtual environment if needed
uvicorn main:app --reload --port 8000
```

**Verify backend is running:**
- Open http://localhost:8000/docs
- Should see FastAPI Swagger documentation

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

**Verify frontend is running:**
- Should see Vite dev server output
- Open http://localhost:5173 (or port shown in terminal)

---

## Test Scenarios

### ✅ Scenario 1: Empty State (First Time User)

**Steps:**
1. Open http://localhost:5173
2. Should see dashboard with map
3. Should see "No monitoring areas yet" message
4. Click "Create First Area" button

**Expected:**
- Dashboard loads without errors
- Map displays (OpenStreetMap)
- Empty state message visible
- Modal opens on button click

---

### ✅ Scenario 2: Create New Monitoring Area

**Steps:**
1. Click "New Monitoring Area" button
2. **Step 1:**
   - Enter name: "Test Forest Area"
   - Select type: "Forest"
   - Click "Next"
3. **Step 2:**
   - Search for location: "Amazon Rainforest"
   - Click first result
   - Click "Draw Area" button
   - Draw a rectangle on map (click and drag)
   - Verify area size shows (should be 1-500 km²)
   - Click "Create"

**Expected:**
- Modal opens with Step 1
- Name validation works (min 3 chars)
- Type selection highlights when clicked
- Next button enabled when valid
- Map loads in Step 2
- Search returns results
- Map centers on selected location
- Rectangle draws correctly
- Area size calculates and displays
- Create button enabled when area valid
- Success: Modal closes, returns to dashboard
- New area appears in dashboard grid
- Area status shows "pending"

**Test Edge Cases:**
- Try name with 2 characters (should disable Next)
- Try name with 101 characters (should disable Next)
- Draw area < 1 km² (should show error)
- Draw area > 500 km² (should show error)

---

### ✅ Scenario 3: View Monitoring Areas

**Steps:**
1. After creating area, verify dashboard shows it
2. Check area card displays:
   - Name
   - Type badge (green for forest, blue for water)
   - Status badge
   - Last Analysis date (should be "N/A")
   - Change percentage (should be "N/A")
3. Verify map shows marker for the area

**Expected:**
- Area card displays correctly
- All information matches created area
- Map marker appears at area location
- Marker color matches type (green=forest, blue=water)
- Clicking marker shows popup with area name

---

### ✅ Scenario 4: View Area Details

**Steps:**
1. Click "View Details" on area card
2. Should navigate to `/areas/{area_id}`
3. Verify page shows:
   - Area name in header
   - Edit and Delete buttons
   - "Trigger Analysis" button
   - Area information card (left)
   - Area map
   - "No analysis results yet" message (right)

**Expected:**
- Page loads without errors
- All area information displayed correctly
- Map shows area boundary as rectangle
- Buttons are enabled (except if analysis in progress)

---

### ✅ Scenario 5: Edit Area Name

**Steps:**
1. On area details page, click "Edit" button
2. Modal opens with current name
3. Change name to "Updated Test Area"
4. Click "Save Changes"

**Expected:**
- Modal opens with current name pre-filled
- Can edit name
- Save button enabled when name changed
- Modal closes on save
- Name updates in header immediately
- Backend receives PATCH request

**Test Edge Cases:**
- Try saving without changes (should close without request)
- Try empty name (button should disable)

---

### ✅ Scenario 6: Trigger Analysis

**Steps:**
1. On area details page, click "Trigger Analysis"
2. Button should show "Analyzing..." with spinner
3. Wait for analysis to complete (~3-5 minutes)

**Expected:**
- Button disabled during analysis
- Shows spinner and "Analyzing..." text
- "Analysis In Progress" card appears
- Page polls for updates every 3 seconds
- When complete:
  - Button re-enables
  - Analysis results appear
  - History updates

**Note:** This will take several minutes as the worker processes Sentinel-2 imagery.

---

### ✅ Scenario 7: Delete Area

**Steps:**
1. On area details page, click "Delete" button
2. Confirmation modal appears
3. Shows area name in warning
4. Click "Delete" button

**Expected:**
- Confirmation modal opens
- Shows warning with area name
- Delete button is red/destructive style
- On confirm:
  - Modal shows loading state
  - Redirects to dashboard
  - Area no longer appears in list

**Test Edge Cases:**
- Click "Cancel" (should close without deleting)
- Check backend - area status should be "deleted"

---

### ✅ Scenario 8: Create Multiple Areas

**Steps:**
1. Create 3 different areas:
   - Forest area in Amazon
   - Water area in Great Lakes
   - Forest area in California
2. Verify all appear in dashboard
3. Check map shows all markers

**Expected:**
- All areas display in grid
- Map shows all markers
- Map auto-zooms to fit all markers
- Different colors for forest vs water

---

### ✅ Scenario 9: Error Handling

**Test Backend Errors:**

1. **Stop backend server**
   - Try to load dashboard
   - Should show error message
   - Error should mention connection failure

2. **Invalid area size**
   - Try to create area > 500 km²
   - Should show backend validation error
   - Error message should mention size limit

3. **Invalid area ID**
   - Navigate to `/areas/invalid-id`
   - Should show "Area not found" error
   - Should have button to return to dashboard

**Expected:**
- All errors display user-friendly messages
- Backend error messages shown when available
- No console errors (check browser DevTools)
- App doesn't crash

---

## Browser DevTools Checks

### Console
- Open browser DevTools (F12)
- Check Console tab
- Should see no errors
- May see API requests logged

### Network Tab
1. Open Network tab
2. Perform actions
3. Verify API calls:
   - `GET /monitoring-areas` - 200 OK
   - `POST /monitoring-areas` - 202 Accepted
   - `PATCH /monitoring-areas/{id}` - 200 OK
   - `DELETE /monitoring-areas/{id}` - 200 OK

### Response Inspection
Click on any API request and check:
- **Request Headers**: Should have `Content-Type: application/json`
- **Request Payload**: Should match expected format
- **Response**: Should match backend structure

---

## Common Issues & Solutions

### Issue: Frontend can't connect to backend
**Solution:**
- Verify backend is running on port 8000
- Check `.env.development` has correct URL
- Restart frontend dev server

### Issue: CORS errors in console
**Solution:**
- Backend needs CORS middleware
- Check backend allows `http://localhost:5173`

### Issue: Map not loading
**Solution:**
- Check internet connection (needs OpenStreetMap tiles)
- Check browser console for errors
- Verify Leaflet CSS is loaded

### Issue: Area size validation not working
**Solution:**
- Check backend validator allows 1-500 km²
- Frontend should show error if outside range

### Issue: Analysis never completes
**Solution:**
- Check worker is running
- Check worker logs for errors
- Verify Earth Engine authentication
- Check GCS permissions

---

## Success Criteria

All tests pass if:
- ✅ Can create monitoring areas
- ✅ All areas display in dashboard
- ✅ Can view area details
- ✅ Can edit area names
- ✅ Can delete areas
- ✅ Can trigger analysis
- ✅ Error messages display correctly
- ✅ No console errors
- ✅ All API calls succeed

---

## Next: Part 2 Testing

After Part 1 is verified:
1. Wait for analysis to complete
2. Verify analysis results display
3. Test new Sentinel-2 image display
4. Test metrics display
5. Test GeoTIFF rendering in Leaflet

---

## Quick Test Commands

```bash
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload

# Terminal 2 - Frontend  
cd frontend
npm run dev

# Terminal 3 - Worker (for analysis)
cd analysis-worker
uvicorn main:app --reload --port 8001
```

Happy Testing! 🧪
