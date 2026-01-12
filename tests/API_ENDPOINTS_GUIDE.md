# API Endpoints Guide - Separate Ingestion and QA Services

## ✅ Yes, It Will Work!

The ingestion and QA-retrieval services are **already designed as separate, independent services**. They can be exposed as separate REST API endpoints without any issues.

---

## Current Service Structure

### 1. **Ingestion Service** (`src/wrappers/ingest_service.py`)
- **Function**: `ingest_one(file_id, folder_path)` - Ingest single PDF
- **Function**: `ingest_all(folder_path)` - Ingest all PDFs
- **Returns**: Dictionary with status, message, file info
- **Dependencies**: SharePoint, Docling, Azure Blob, Qdrant
- **Independence**: ✅ Fully independent from QA service

### 2. **QA/Retrieval Service** (`src/wrappers/qa_service.py`)
- **Function**: `answer_question(user_query)` - Answer questions
- **Returns**: Dictionary with answer_markdown, source_file, confidence
- **Dependencies**: Qdrant, OpenAI API
- **Independence**: ✅ Fully independent from ingestion service

---

## Why They Work Separately

### ✅ **No Shared State**
- Ingestion writes to Qdrant
- QA reads from Qdrant
- No direct coupling between services

### ✅ **Different Dependencies**
- Ingestion: Requires SharePoint, Docling, Azure Blob
- QA: Requires Qdrant (which ingestion populates) + OpenAI

### ✅ **Different Execution Patterns**
- Ingestion: Long-running, CPU/memory intensive
- QA: Fast queries, network-bound (OpenAI API)

### ✅ **Already Return Structured Data**
- Both services return dictionaries
- Easy to serialize as JSON responses
- No modifications needed to wrapper functions

---

## Example API Implementation

I've created `api_service.py` with FastAPI that exposes:

### **Endpoint 1: QA/Retrieval**
```
POST /api/qa/answer
Body: {"question": "What is the backup policy?"}
Response: {
  "success": true,
  "answer_markdown": "...",
  "source_file": "...",
  "confidence_score": 0.95
}
```

### **Endpoint 2: Ingestion (Single)**
```
POST /api/ingest/one
Body: {"file_id": "optional", "folder_path": "Shared Documents"}
Response: {
  "success": true,
  "message": "Ingested filename.pdf",
  "file": "filename.pdf"
}
```

### **Endpoint 3: Ingestion (All)**
```
POST /api/ingest/all
Body: {"folder_path": "Shared Documents"}
Response: {
  "success": true,
  "processed": 5,
  "failed": 0,
  "errors": []
}
```

---

## Architecture with Separate Endpoints

```
┌─────────────────────────────────────────────┐
│          API Server (FastAPI)               │
│  ┌───────────────────────────────────────┐  │
│  │  POST /api/qa/answer                 │  │
│  │  └─> qa_service.answer_question()    │  │
│  │      └─> Qdrant (read)               │  │
│  │      └─> OpenAI API                  │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │  POST /api/ingest/one                │  │
│  │  └─> ingest_service.ingest_one()     │  │
│  │      └─> SharePoint (read)           │  │
│  │      └─> Docling (process)           │  │
│  │      └─> Azure Blob (write)          │  │
│  │      └─> Qdrant (write)              │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
        │                    │
        ├─ Qdrant (shared) ──┤
        │                    │
        ├─ Azure Blob        │
        ├─ SharePoint        │
        └─ OpenAI API ───────┘
```

---

## Benefits of Separate Endpoints

### 1. **Independent Scaling**
- Scale ingestion and QA services separately
- Ingestion: CPU/memory intensive, batch processing
- QA: Network-bound, real-time queries

### 2. **Different Security/Authorization**
- Ingestion: Admin/backend service (sensitive operations)
- QA: User-facing API (read-only, public)

### 3. **Independent Deployment**
- Deploy updates to ingestion without affecting QA
- Deploy updates to QA without affecting ingestion
- Different versioning strategies

### 4. **Better Monitoring**
- Track ingestion metrics separately
- Track QA performance separately
- Identify bottlenecks independently

### 5. **Rate Limiting**
- Different rate limits for ingestion vs QA
- Ingestion: Lower rate (resource-intensive)
- QA: Higher rate (lightweight queries)

---

## Usage Examples

### Using the API Endpoints

#### QA Endpoint (User Questions)
```bash
# Ask a question
curl -X POST http://localhost:8000/api/qa/answer \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the backup retention policy?"}'

# Response
{
  "success": true,
  "answer_markdown": "The backup retention policy is...",
  "source_file": "Barracuda_Backup_Policy_v1_0.pdf",
  "confidence_score": 0.92
}
```

#### Ingestion Endpoint (Admin/Backend)
```bash
# Ingest a single PDF
curl -X POST http://localhost:8000/api/ingest/one \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "Shared Documents"}'

# Response
{
  "success": true,
  "message": "Ingested document.pdf",
  "file": "document.pdf"
}

# Ingest all PDFs
curl -X POST http://localhost:8000/api/ingest/all \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "Shared Documents"}'

# Response
{
  "success": true,
  "processed": 5,
  "failed": 0,
  "errors": []
}
```

---

## Running the API Service

### Install FastAPI (if not already installed)
```bash
uv pip install fastapi uvicorn
```

### Run the API Server
```bash
# Activate environment
.\1440_env\Scripts\Activate.ps1

# Set PYTHONPATH and load .env
$env:PYTHONPATH = "$PWD;$PWD\src"
Get-Content .env | ForEach-Object {
    $p=$_ -split '=',2
    if($p.Length -eq 2) {
        $val = $p[1].Trim().Trim('"', "'")
        set-item -path "env:$($p[0].Trim())" -value $val
    }
}

# Run API server
python api_service.py
```

### Access API
- **API Server**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)

---

## Integration with Existing Services

### Current Setup
- ✅ Streamlit UI (`ui/chat.py`) - Uses `qa_service.answer_question()`
- ✅ CLI scripts - Use wrapper functions directly
- ✅ Tests - Use wrapper functions directly

### With API Endpoints
- ✅ Streamlit UI - Can call API endpoint instead (optional)
- ✅ CLI scripts - Can call API endpoint instead (optional)
- ✅ External clients - Can call API endpoints
- ✅ Web applications - Can call API endpoints
- ✅ Mobile apps - Can call API endpoints

**All existing code continues to work!** The wrapper functions remain unchanged.

---

## Deployment Options

### Option 1: Single API Server (Both Endpoints)
- One FastAPI server with both endpoints
- Simpler deployment
- Shared resources
- Good for: Single VM deployment

### Option 2: Separate Services (Recommended for Production)
- **Ingestion Service**: Separate API server
- **QA Service**: Separate API server
- Independent scaling
- Good for: Microservices architecture, Kubernetes

### Option 3: Hybrid
- **QA Service**: Public API endpoint
- **Ingestion Service**: Internal/Admin endpoint (same or different server)
- Different authentication/authorization
- Good for: Production with security requirements

---

## Security Considerations

### Separate Endpoints Allow:
1. **Different Authentication**
   - Ingestion: Admin API key, Azure AD authentication
   - QA: User tokens, public access (read-only)

2. **Different Rate Limits**
   - Ingestion: Low rate (1-5 requests/minute)
   - QA: Higher rate (100+ requests/minute)

3. **Different Access Control**
   - Ingestion: Internal/VPN only
   - QA: Public with API key

4. **Different Monitoring**
   - Track ingestion separately from QA
   - Different alerting thresholds

---

## Conclusion

**✅ Yes, exposing ingestion and QA as separate endpoints will work perfectly!**

- Services are already independent
- No code changes needed to wrapper functions
- Easy to expose as REST API endpoints
- Better architecture for production
- Allows independent scaling and deployment

The `api_service.py` file provides a ready-to-use FastAPI implementation with both endpoints.
