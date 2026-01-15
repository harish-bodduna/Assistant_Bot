# 1440 Bot API v2.0 - Refactored Structure

## New Structure

The API has been refactored into a clean FastAPI structure:

```
1440_Bot/
├── app/              # FastAPI application setup
├── routers/          # API route handlers
├── services/          # Business logic layer
├── schemas/           # Pydantic models
└── src/              # Existing code (unchanged)
```

## Running the API

### Start the server:
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --reload --port 8000
```

## Endpoints

### 1. Health Check
```
GET /health
```

### 2. Q&A (Streaming SSE)
```
POST /api/qa/answer
Content-Type: application/json

{
  "question": "What is the backup policy?"
}

Response: text/event-stream
data: {"chunk": "### Step 1"}
data: {"chunk": "\n\nLogin to..."}
data: [DONE]
```

### 3. Blob Ingestion (for Azure Function)
```
POST /api/ingest/blob
Content-Type: application/json

{
  "blob_name": "document.pdf",
  "container_name": "raw-files"
}
```

## Testing

### Test QA endpoint with streaming:
```bash
curl -N http://localhost:8000/api/qa/answer \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}' \
  -H "Accept: text/event-stream"
```

### Test blob ingestion:
```bash
curl -X POST http://localhost:8000/api/ingest/blob \
  -H "Content-Type: application/json" \
  -d '{"blob_name": "document.pdf", "container_name": "raw-files"}'
```

## Migration Notes

- Old API: `tests/api_service.py` (kept for comparison)
- New API: `main.py` (entry point)
- All `src/` code remains unchanged
- Once new API is tested and confirmed, old API can be removed
