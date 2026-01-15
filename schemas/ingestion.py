"""Ingestion request/response models."""
from pydantic import BaseModel


class BlobIngestRequest(BaseModel):
    """Request model for blob ingestion endpoint.
    
    The folder_name is the document name without extension (e.g., 
    "1440-Microsoft_Multifactor_Authentication_Documentation").
    This corresponds to a folder in raw-files container containing the PDF.
    """
    folder_name: str
    raw_files_container: str = "raw-files"
    processed_files_container: str = "processed-files"


class IngestResponse(BaseModel):
    """Response model for ingestion endpoint."""
    success: bool
    message: str
    file: str | None = None
