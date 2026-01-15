"""Ingestion business logic service."""
import os
from datetime import datetime
from typing import Dict, Any
from azure.storage.blob import BlobServiceClient
from src.text_indexing.layout_ingestor import LayoutAwareIngestor
from src.config.settings import get_settings


async def ingest_from_blob(
    folder_name: str,
    raw_files_container: str = "raw-files",
    processed_files_container: str = "processed-files"
) -> Dict[str, Any]:
    """
    Ingest a PDF from Azure Blob Storage folder structure.
    
    This function:
    1. Checks if document is already processed in processed-files container
    2. Lists blobs in raw-files/{folder_name}/ to find the PDF file
    3. Downloads and processes the PDF with LayoutAwareIngestor
    4. Stores embeddings in Qdrant and images in Azure Blob
    5. Creates status.txt in processed-files/{folder_name}/ to mark as processed
    
    Args:
        folder_name: Document name without extension (e.g., "1440-Microsoft_Multifactor_Authentication_Documentation")
        raw_files_container: Container name for raw files (default: "raw-files")
        processed_files_container: Container name for processed files (default: "processed-files")
        
    Returns:
        Dictionary with ingestion status
    """
    settings = get_settings()
    
    # Get connection string
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is required")
    
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    
    # Check if already processed
    processed_folder_path = f"{folder_name}/status.txt"
    processed_container_client = blob_service.get_container_client(processed_files_container)
    
    try:
        # Check if status.txt exists in processed-files
        status_blob_client = processed_container_client.get_blob_client(processed_folder_path)
        if status_blob_client.exists():
            return {
                "ok": False,
                "message": f"Document '{folder_name}' is already processed (status.txt exists)",
                "file": folder_name,
                "skipped": True
            }
    except Exception as e:
        # If container doesn't exist or other error, we'll continue (might be first time)
        pass
    
    # List blobs in raw-files/{folder_name}/ to find PDF
    raw_container_client = blob_service.get_container_client(raw_files_container)
    folder_prefix = f"{folder_name}/"
    
    pdf_blob_name = None
    try:
        # List all blobs in the folder
        blobs = list(raw_container_client.list_blobs(name_starts_with=folder_prefix))
        
        # Find the PDF file (ignore image files)
        for blob in blobs:
            blob_name_lower = blob.name.lower()
            # Skip image files - we extract images separately using docling
            if blob_name_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
                continue
            # Look for PDF file
            if blob_name_lower.endswith('.pdf'):
                pdf_blob_name = blob.name
                break
        
        if not pdf_blob_name:
            return {
                "ok": False,
                "message": f"No PDF file found in folder '{folder_name}' in container '{raw_files_container}'",
                "file": folder_name
            }
    except Exception as e:
        return {
            "ok": False,
            "message": f"Failed to list blobs in folder '{folder_name}': {str(e)}",
            "file": folder_name
        }
    
    # Download PDF
    try:
        pdf_blob_client = raw_container_client.get_blob_client(pdf_blob_name)
        pdf_bytes = pdf_blob_client.download_blob().readall()
    except Exception as e:
        return {
            "ok": False,
            "message": f"Failed to download PDF '{pdf_blob_name}': {str(e)}",
            "file": folder_name
        }
    
    # Extract file name from blob path
    file_name = pdf_blob_name.split("/")[-1] if "/" in pdf_blob_name else pdf_blob_name
    
    # Get banned images directory from environment
    banned_images_dir = os.getenv("BANNED_IMAGES_DIR")
    
    # Process with LayoutAwareIngestor
    try:
        ingestor = LayoutAwareIngestor(collection="manuals_text", banned_images_dir=banned_images_dir)
        ingestor.index_pdf(pdf_bytes, file_name=file_name)
        
        # Create status.txt in processed-files to mark as processed
        try:
            # Ensure processed-files container exists
            try:
                processed_container_client.create_container()
            except Exception:
                pass  # Container already exists
            
            # Upload status.txt with timestamp
            timestamp = datetime.utcnow().isoformat()
            status_content = f"Processed: {file_name}\nStatus: Success\nTimestamp: {timestamp}"
            status_blob_client.upload_blob(status_content, overwrite=True)
        except Exception as e:
            # Log warning but don't fail - ingestion was successful
            print(f"Warning: Failed to create status.txt: {str(e)}")
        
        return {
            "ok": True,
            "message": f"Successfully ingested {file_name}",
            "file": file_name
        }
    except Exception as e:
        return {
            "ok": False,
            "message": f"Ingestion failed: {str(e)}",
            "file": file_name
        }
