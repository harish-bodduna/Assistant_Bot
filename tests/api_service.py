#!/usr/bin/env python3
"""
API Service for 1440 Bot
Exposes ingestion and QA-retrieval as separate REST endpoints
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Add project root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
except ImportError:
    print("ERROR: FastAPI not installed. Install with: uv pip install fastapi uvicorn")
    sys.exit(1)

from src.wrappers.ingest_service import ingest_one, ingest_all
from src.wrappers.qa_service import answer_question

# Create FastAPI app
app = FastAPI(
    title="1440 Bot API",
    description="API for document ingestion and QA retrieval",
    version="1.0.0"
)


# Request/Response models
class QuestionRequest(BaseModel):
    question: str


class IngestRequest(BaseModel):
    file_id: Optional[str] = None
    folder_path: Optional[str] = "Shared Documents"


class IngestAllRequest(BaseModel):
    folder_path: Optional[str] = "Shared Documents"


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "1440-bot-api"}


# QA/Retrieval Endpoint
@app.post("/api/qa/answer")
async def qa_endpoint(request: QuestionRequest):
    """
    Answer a question using QA-retrieval service.
    
    This endpoint:
    - Searches Qdrant for relevant documents
    - Retrieves context with images
    - Generates answer using OpenAI GPT-5.2
    - Returns markdown with interleaved text and images
    """
    try:
        result = answer_question(request.question)
        
        if result.get("ok"):
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "answer_markdown": result.get("answer_markdown"),
                    "source_file": result.get("source_file"),
                    "confidence_score": result.get("confidence_score"),
                }
            )
        else:
            return JSONResponse(
                status_code=404 if "No relevant" in result.get("message", "") else 500,
                content={
                    "success": False,
                    "error": result.get("message"),
                    "answer_markdown": None,
                    "source_file": result.get("source_file"),
                    "confidence_score": result.get("confidence_score", 0.0),
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# Ingestion Endpoint - Single Document
@app.post("/api/ingest/one")
async def ingest_one_endpoint(request: IngestRequest):
    """
    Ingest a single PDF from SharePoint.
    
    This endpoint:
    - Downloads PDF from SharePoint
    - Parses with Docling
    - Uploads images to Azure Blob Storage
    - Stores markdown + embeddings in Qdrant
    """
    try:
        result = ingest_one(
            file_id=request.file_id,
            folder_path=request.folder_path
        )
        
        if result.get("ok"):
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": result.get("message"),
                    "file": result.get("file"),
                }
            )
        else:
            return JSONResponse(
                status_code=404 if "No PDF found" in result.get("message", "") else 500,
                content={
                    "success": False,
                    "message": result.get("message"),
                    "file": result.get("file"),
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# Ingestion Endpoint - All Documents
@app.post("/api/ingest/all")
async def ingest_all_endpoint(request: IngestAllRequest):
    """
    Ingest all PDFs from SharePoint folder.
    
    This endpoint:
    - Finds all PDFs in the specified folder
    - Processes each one (download, parse, store)
    - Returns summary with counts
    """
    try:
        result = ingest_all(folder_path=request.folder_path)
        
        status_code = 200 if result.get("ok") or result.get("processed", 0) > 0 else 500
        
        return JSONResponse(
            status_code=status_code,
            content={
                "success": result.get("ok", False),
                "message": result.get("message"),
                "processed": result.get("processed", 0),
                "failed": result.get("failed", 0),
                "errors": result.get("errors", []),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("  1440 Bot API Service")
    print("="*60)
    print("\nEndpoints:")
    print("  POST /api/qa/answer      - Answer questions")
    print("  POST /api/ingest/one     - Ingest single PDF")
    print("  POST /api/ingest/all     - Ingest all PDFs")
    print("  GET  /health             - Health check")
    print("\nAPI Docs: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
