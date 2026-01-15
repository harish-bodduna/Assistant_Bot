"""Ingestion router for blob ingestion endpoint."""
from fastapi import APIRouter, HTTPException
from schemas.ingestion import BlobIngestRequest, IngestResponse
from services.ingestion_service import ingest_from_blob

router = APIRouter()


@router.post("/blob", response_model=IngestResponse)
async def ingest_blob(request: BlobIngestRequest):
    """
    Ingest PDF from Azure Blob Storage folder structure.
    
    This endpoint is called by Azure Function when a new folder is created in raw-files.
    
    Flow:
    1. Checks processed-files/{folder_name}/status.txt to see if already processed
    2. Lists blobs in raw-files/{folder_name}/ to find the PDF (ignores image files)
    3. Downloads and processes the PDF with LayoutAwareIngestor
    4. Stores embeddings in Qdrant and images in Azure Blob
    5. Creates status.txt in processed-files/{folder_name}/ to mark as processed
    
    Args:
        request: BlobIngestRequest with folder_name (document name without extension)
        
    Returns:
        IngestResponse with success status and message
    """
    try:
        result = await ingest_from_blob(
            folder_name=request.folder_name,
            raw_files_container=request.raw_files_container,
            processed_files_container=request.processed_files_container
        )
        
        # If skipped (already processed), return success with skip message
        if result.get("skipped"):
            return IngestResponse(
                success=True,
                message=result.get("message", "Document already processed"),
                file=result.get("file")
            )
        
        if not result.get("ok"):
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Ingestion failed")
            )
        
        return IngestResponse(
            success=result.get("ok", False),
            message=result.get("message", ""),
            file=result.get("file")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
