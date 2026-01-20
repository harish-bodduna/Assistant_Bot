"""Script to delete status files and re-ingest all documents with new format."""
import os
import asyncio
from azure.storage.blob import BlobServiceClient
from services.ingestion_service import ingest_from_blob


async def delete_status_and_reingest():
    """Delete status.txt files and re-ingest all documents."""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        print("ERROR: AZURE_STORAGE_CONNECTION_STRING not found in environment")
        return
    
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    raw_container = blob_service.get_container_client("raw-files")
    processed_container = blob_service.get_container_client("processed-files")
    
    # List all blobs to find unique folder names
    print("Scanning raw-files container for documents...")
    folders = set()
    
    try:
        blobs = raw_container.list_blobs()
        for blob in blobs:
            # Extract folder name (first part of path)
            if "/" in blob.name:
                folder_name = blob.name.split("/")[0]
                folders.add(folder_name)
            elif blob.name.lower().endswith('.pdf'):
                # PDF at root level - use filename without extension as folder
                folder_name = os.path.splitext(blob.name)[0]
                folders.add(folder_name)
        
        folders = sorted(list(folders))
        print(f"Found {len(folders)} document folders:")
        for i, folder in enumerate(folders, 1):
            print(f"  {i}. {folder}")
        
        if not folders:
            print("No documents found in raw-files container.")
            return
        
        # Delete status.txt files first
        print("\n" + "="*60)
        print("Deleting status.txt files to allow re-ingestion...")
        print("="*60 + "\n")
        
        deleted_count = 0
        for folder_name in folders:
            status_path = f"{folder_name}/status.txt"
            try:
                status_blob = processed_container.get_blob_client(status_path)
                if status_blob.exists():
                    status_blob.delete_blob()
                    print(f"  [DELETED] {folder_name}/status.txt")
                    deleted_count += 1
            except Exception as e:
                print(f"  [WARN] Could not delete {folder_name}/status.txt: {e}")
        
        print(f"\nDeleted {deleted_count} status.txt files\n")
        
        print("="*60)
        print("Starting re-ingestion process with new Document_parsing-2 format...")
        print("="*60 + "\n")
        
        # Ingest each folder
        results = []
        for idx, folder_name in enumerate(folders, 1):
            print(f"[{idx}/{len(folders)}] Processing: {folder_name}")
            try:
                result = await ingest_from_blob(
                    folder_name=folder_name,
                    raw_files_container="raw-files",
                    processed_files_container="processed-files"
                )
                
                if result.get("skipped"):
                    print(f"  [SKIP] {result.get('message')}")
                    results.append({"folder": folder_name, "status": "skipped", "message": result.get("message")})
                elif result.get("ok"):
                    print(f"  [OK] {result.get('message')}")
                    results.append({"folder": folder_name, "status": "success", "message": result.get("message")})
                else:
                    print(f"  [FAIL] {result.get('message')}")
                    results.append({"folder": folder_name, "status": "failed", "message": result.get("message")})
            except Exception as e:
                print(f"  [ERROR] {str(e)}")
                results.append({"folder": folder_name, "status": "error", "message": str(e)})
            
            print()  # Empty line between documents
        
        # Summary
        print("="*60)
        print("RE-INGESTION SUMMARY")
        print("="*60)
        successful = sum(1 for r in results if r["status"] == "success")
        skipped = sum(1 for r in results if r["status"] == "skipped")
        failed = sum(1 for r in results if r["status"] in ["failed", "error"])
        
        print(f"Total: {len(results)}")
        print(f"[OK] Successful: {successful}")
        print(f"[SKIP] Skipped: {skipped}")
        print(f"[FAIL] Failed: {failed}")
        
        if failed > 0:
            print("\nFailed documents:")
            for r in results:
                if r["status"] in ["failed", "error"]:
                    print(f"  - {r['folder']}: {r['message']}")
    
    except Exception as e:
        print(f"ERROR: Failed to process documents: {str(e)}")


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(delete_status_and_reingest())
