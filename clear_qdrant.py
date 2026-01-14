"""
Script to clear all documents from Qdrant collection.
"""
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

load_dotenv()

def clear_qdrant_collection(collection_name: str = "manuals_text"):
    """Delete all points from a Qdrant collection."""
    client = QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY"),
        check_compatibility=False,
    )
    
    if not client.collection_exists(collection_name):
        print(f"Collection '{collection_name}' does not exist. Nothing to clear.")
        return
    
    # Get collection info
    coll_info = client.get_collection(collection_name)
    point_count = coll_info.points_count
    print(f"Collection '{collection_name}' has {point_count} points.")
    
    if point_count == 0:
        print("Collection is already empty.")
        return
    
    # Delete all points by scrolling and deleting
    print(f"Deleting all points from '{collection_name}'...")
    
    # Scroll through all points and collect IDs
    all_ids = []
    offset = None
    while True:
        result = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        points, next_offset = result
        
        if not points:
            break
            
        all_ids.extend([point.id for point in points])
        
        if next_offset is None:
            break
        offset = next_offset
    
    # Delete all points
    if all_ids:
        client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(
                points=all_ids
            )
        )
        print(f"Deleted {len(all_ids)} points from '{collection_name}'.")
    else:
        print("No points found to delete.")
    
    # Verify
    coll_info = client.get_collection(collection_name)
    print(f"Collection now has {coll_info.points_count} points.")

if __name__ == "__main__":
    clear_qdrant_collection("manuals_text")
