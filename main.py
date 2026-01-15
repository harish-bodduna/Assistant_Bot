"""Application entry point for FastAPI server."""
import uvicorn
from app.main import app

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  1440 Bot API Service v2.0")
    print("="*60)
    print("\nEndpoints:")
    print("  POST /api/qa/answer      - Answer questions (streaming SSE)")
    print("  POST /api/ingest/blob   - Ingest from Azure Blob")
    print("  GET  /health            - Health check")
    print("\nAPI Docs: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
