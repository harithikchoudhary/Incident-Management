# Swagger UI Setup Instructions

## Problem
The CDN (cdn.jsdelivr.net) is being blocked by your firewall/network, preventing Swagger UI from loading.

## Solution Implemented
I've updated the FastAPI application to:
1. Try loading Swagger UI from local files first
2. Fallback to CDN (unpkg.com) if local files don't exist
3. Show a helpful error page with API documentation if both fail

## Commands to Run

### Option 1: Try the CDN Fallback (Quickest)
1. **Restart the FastAPI server:**
   ```bash
   cd e:\incident-multiagent\Incident-Management\backend
   # Press Ctrl+C to stop the current server if running
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Try accessing Swagger UI:**
   - Open browser: http://127.0.0.1:8000/docs
   - Wait a few seconds for it to load
   - If unpkg.com is not blocked, it should work

### Option 2: Install Local Swagger UI (Recommended)
This completely eliminates CDN dependency:

1. **Download Swagger UI locally:**
   ```bash
   cd e:\incident-multiagent\Incident-Management\backend
   python setup_swagger.py
   ```

2. **Restart the server:**
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Access Swagger UI:**
   - Open browser: http://127.0.0.1:8000/docs
   - Should now work without any CDN!

### Option 3: Use the Raw OpenAPI Spec
If Swagger UI still doesn't work:

1. **View the raw API specification:**
   - Open: http://127.0.0.1:8000/openapi.json

2. **Import into an API client:**
   - **Postman**: Import → Link → http://127.0.0.1:8000/openapi.json
   - **Insomnia**: Create → Import From → URL
   - **Bruno**: Collection → Import → OpenAPI
   - **VS Code REST Client**: Create a .http file with the endpoints

## Verification

After restarting the server, you should see one of these:

### Success ✅
- Full interactive Swagger UI documentation
- Can test all API endpoints directly in the browser

### Fallback ✅
- Helpful error page listing all endpoints
- Link to download OpenAPI spec
- Instructions for using API clients

## Available Endpoints

Once accessible, you'll see documentation for:

- **Health & Dashboard**
  - GET /api/health
  - GET /api/dashboard

- **Incidents**
  - GET /api/incidents
  - GET /api/incidents/search
  - GET /api/incidents/{id}
  - GET /api/incidents/{id}/conversation
  - POST /api/incidents/analyze
  - POST /api/incidents/chat

- **Data Ingestion**
  - POST /api/ingestion/mock-chat

## Troubleshooting

**If you still see a blank page:**
1. Check browser console (F12) for errors
2. Try a different browser (Chrome/Firefox/Edge)
3. Check if another service is using port 8000
4. Verify the server started without errors

**If setup_swagger.py fails:**
- Your network may block GitHub downloads
- Manually download from: https://github.com/swagger-api/swagger-ui/releases
- Extract the `dist` folder to: `backend/app/static/swagger-ui/`
