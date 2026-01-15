"""
Utility script to clear all documents from Qdrant collection.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.http import models
from src.config.settings import get_settings


def clear_qdrant_collection(collection_name: str = "manuals_text") -> None:
    """Delete all points from a Qdrant collection."""
    settings = get_settings()
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
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
