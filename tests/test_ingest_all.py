#!/usr/bin/env python3
"""
Test script for ingesting all PDFs from SharePoint
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wrappers.ingest_service import ingest_all


def main():
    """Run batch ingestion"""
    print("\n" + "="*60)
    print("  Batch Ingestion - All PDFs from SharePoint")
    print("="*60 + "\n")
    
    try:
        result = ingest_all()
        
        print("\n" + "="*60)
        print("Ingestion Summary")
        print("="*60)
        print(f"  Processed: {result.get('processed', 0)}")
        print(f"  Failed: {result.get('failed', 0)}")
        print(f"  Status: {'SUCCESS' if result.get('ok') else 'PARTIAL'}")
        
        if result.get('errors'):
            print(f"\nErrors ({len(result['errors'])}):")
            for error in result['errors']:
                print(f"  - {error}")
        
        if result.get('ok'):
            print("\n[SUCCESS] All PDFs ingested successfully!")
            return 0
        elif result.get('processed', 0) > 0:
            print("\n[PARTIAL] Some PDFs were ingested, but some failed.")
            return 0
        else:
            print("\n[FAILED] No PDFs were ingested.")
            return 1
            
    except Exception as e:
        print(f"\n[ERROR] Exception during batch ingestion: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
