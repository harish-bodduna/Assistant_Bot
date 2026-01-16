"""Application entry point for FastAPI server."""
import uvicorn

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
    
    # Use import string format to enable reload mode
    uvicorn.run(
        "app.app:app",  # Import string instead of app object
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
