"""
Script to ingest the Multifactor Authentication document with new code.
"""
import sys
from pathlib import Path

# Add project root to sys.path for imports
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.wrappers.ingest_service import ingest_one
from src.bridge.sharepoint_connector import SharePointConnector
from src.config.settings import get_settings

def find_mfa_document():
    """Find the MFA document in SharePoint."""
    settings = get_settings()
    sp = SharePointConnector(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        site_id=settings.sharepoint_site_id,
        drive_id=settings.sharepoint_drive_id,
    )
    
    folder_path = settings.sharepoint_folder_path or "Shared Documents"
    files = sp.list_files(folder_path=folder_path)
    
    # Look for MFA document
    mfa_keywords = ["multifactor", "mfa", "authentication"]
    
    for f in files:
        name = f.get("name") if isinstance(f, dict) else getattr(f, "name", "")
        if name.lower().endswith(".pdf"):
            name_lower = name.lower()
            if any(keyword in name_lower for keyword in mfa_keywords):
                print(f"Found MFA document: {name}")
                return f.get("id") if isinstance(f, dict) else getattr(f, "id", None)
    
    print("MFA document not found. Available PDFs:")
    for f in files:
        name = f.get("name") if isinstance(f, dict) else getattr(f, "name", "")
        if name.lower().endswith(".pdf"):
            print(f"  - {name}")
    
    return None

def main():
    print("=" * 60)
    print("Ingesting Multifactor Authentication Document")
    print("=" * 60)
    
    # Find MFA document
    mfa_file_id = find_mfa_document()
    
    if not mfa_file_id:
        print("\nError: Could not find MFA document in SharePoint.")
        print("Please check the folder path and document name.")
        return 1
    
    # Ingest the document
    print(f"\nIngesting document with ID: {mfa_file_id}")
    result = ingest_one(file_id=mfa_file_id)
    
    if result.get("ok"):
        print(f"\n[SUCCESS] Successfully ingested: {result.get('file')}")
        print(f"  Message: {result.get('message')}")
        return 0
    else:
        print(f"\n[FAILED] Ingestion failed: {result.get('file')}")
        print(f"  Error: {result.get('message')}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
