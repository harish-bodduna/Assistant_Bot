#!/usr/bin/env python3
"""
Test script for ingestion functionality
Tests downloading PDFs from SharePoint and ingesting them into Qdrant
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.wrappers.ingest_service import ingest_one, ingest_all


def test_ingest_one():
    """Test ingesting a single PDF from SharePoint"""
    print("\n" + "="*60)
    print("Testing: ingest_one() - Single PDF Ingestion")
    print("="*60 + "\n")
    
    try:
        result = ingest_one()
        
        if result.get("ok"):
            print(f"[SUCCESS] Ingestion completed!")
            print(f"  File: {result.get('file', 'unknown')}")
            print(f"  Message: {result.get('message', '')}")
            return True
        else:
            print(f"[FAILED] Ingestion failed:")
            print(f"  File: {result.get('file', 'unknown')}")
            print(f"  Message: {result.get('message', '')}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception during ingestion: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ingest_all():
    """Test ingesting all PDFs from SharePoint (optional, can be commented out)"""
    print("\n" + "="*60)
    print("Testing: ingest_all() - All PDFs Ingestion")
    print("="*60 + "\n")
    print("Note: This will ingest ALL PDFs in the folder. Use with caution!")
    print("Skipping ingest_all() for now. Uncomment to test.")
    return True
    
    # Uncomment to test ingest_all:
    # try:
    #     result = ingest_all()
    #     
    #     if result.get("ok"):
    #         print(f"[SUCCESS] Batch ingestion completed!")
    #         print(f"  Processed: {result.get('processed', 0)}")
    #         print(f"  Failed: {result.get('failed', 0)}")
    #         return True
    #     else:
    #         print(f"[PARTIAL] Some ingestions failed:")
    #         print(f"  Processed: {result.get('processed', 0)}")
    #         print(f"  Failed: {result.get('failed', 0)}")
    #         if result.get('errors'):
    #             for error in result['errors']:
    #                 print(f"    - {error}")
    #         return result.get('processed', 0) > 0
    # except Exception as e:
    #     print(f"[ERROR] Exception during batch ingestion: {e}")
    #     import traceback
    #     traceback.print_exc()
    #     return False


def main():
    """Run ingestion tests"""
    print("\n" + "="*60)
    print("  1440 Bot Ingestion Test")
    print("="*60)
    
    results = {
        "Single PDF Ingestion": test_ingest_one(),
        # "Batch Ingestion": test_ingest_all(),  # Commented out for safety
    }
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {test_name:30s} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("  ALL TESTS PASSED!")
        print("="*60)
        print("\nNext steps:")
        print("  1. Check Qdrant collections: http://localhost:6333/dashboard")
        print("  2. Check markdown_exports/ folder for exported markdown")
        print("  3. Test QA functionality with test_qa.py")
        return 0
    else:
        print("  SOME TESTS FAILED")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
