#!/usr/bin/env python3
"""
Comprehensive setup test script for 1440 Bot
Tests environment, dependencies, and connectivity
"""
import sys
import os
from pathlib import Path

def print_header(text: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def test_python_version():
    """Test Python version meets requirements"""
    print_header("Testing Python Version")
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 12:
        print("[OK] Python version meets requirement (>=3.12)")
        return True
    else:
        print("[FAIL] Python version does not meet requirement (>=3.12)")
        return False

def test_core_imports():
    """Test core dependencies can be imported"""
    print_header("Testing Core Dependencies")
    imports_to_test = [
        ("docling.document_converter", "DocumentConverter"),
        ("qdrant_client", "QdrantClient"),
        ("openai", "OpenAI"),
        ("azure.storage.blob", "BlobServiceClient"),
        ("azure.identity", "ClientSecretCredential"),
        ("llama_index", None),
        ("pydantic_ai", "Agent"),
        ("dspy", None),
    ]
    
    results = {}
    for module_name, item_name in imports_to_test:
        try:
            if item_name:
                # Handle submodule imports like docling.document_converter
                if '.' in module_name:
                    parts = module_name.split('.')
                    module = __import__(module_name, fromlist=[parts[-1]])
                    getattr(module, item_name)
                    print(f"[OK] {module_name}.{item_name}")
                else:
                    module = __import__(module_name, fromlist=[item_name])
                    getattr(module, item_name)
                    print(f"[OK] {module_name}.{item_name}")
                results[module_name] = True
            else:
                __import__(module_name)
                print(f"[OK] {module_name}")
                results[module_name] = True
        except ImportError as e:
            print(f"[FAIL] {module_name}: {e}")
            results[module_name] = False
        except AttributeError as e:
            print(f"[FAIL] {module_name}.{item_name}: {e}")
            results[module_name] = False
    
    return all(results.values())

def test_qdrant_connection():
    """Test connection to Qdrant"""
    print_header("Testing Qdrant Connection")
    try:
        from qdrant_client import QdrantClient
        import os
        
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        print(f"Connecting to Qdrant at: {qdrant_url}")
        
        client = QdrantClient(url=qdrant_url, timeout=5, check_compatibility=False)
        collections = client.get_collections()
        print(f"[OK] Successfully connected to Qdrant")
        print(f"  Collections found: {len(collections.collections)}")
        for coll in collections.collections:
            print(f"    - {coll.name}")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to connect to Qdrant: {e}")
        return False

def test_environment_variables():
    """Test critical environment variables are set"""
    print_header("Testing Environment Variables")
    
    required_vars = [
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID", 
        "AZURE_CLIENT_SECRET",
        "SHAREPOINT_SITE_ID",
        "OPENAI_API_KEY",
        "QDRANT_URL",
        "AZURE_STORAGE_CONNECTION_STRING",
    ]
    
    optional_vars = [
        "SHAREPOINT_DRIVE_ID",
        "SHAREPOINT_FOLDER_PATH",
        "OPENAI_API_BASE",
        "QDRANT_API_KEY",
    ]
    
    all_set = True
    print("Required variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "SECRET" in var or "KEY" in var or "CONNECTION_STRING" in var:
                display_value = f"{value[:10]}... (hidden)"
            else:
                display_value = value
            print(f"  [OK] {var}: {display_value}")
        else:
            print(f"  [FAIL] {var}: NOT SET")
            all_set = False
    
    print("\nOptional variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  [OK] {var}: {value[:50]}...")
        else:
            print(f"  [-] {var}: (not set, optional)")
    
    return all_set

def test_project_imports():
    """Test project modules can be imported"""
    print_header("Testing Project Modules")
    
    project_modules = [
        "src.config.settings",
        "src.bridge.sharepoint_connector",
        "src.text_indexing.storage",
        "src.retrieval.multimodal_service",
    ]
    
    results = {}
    for module_name in project_modules:
        try:
            __import__(module_name)
            print(f"[OK] {module_name}")
            results[module_name] = True
        except ImportError as e:
            print(f"[FAIL] {module_name}: {e}")
            results[module_name] = False
        except Exception as e:
            # Some modules might fail due to missing env vars, that's OK for import test
            print(f"[WARN] {module_name}: Imported but initialization failed (expected if env vars missing)")
            results[module_name] = True
    
    return all(results.values())

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  1440 Bot Setup Test Suite")
    print("="*60)
    
    results = {
        "Python Version": test_python_version(),
        "Core Dependencies": test_core_imports(),
        "Qdrant Connection": test_qdrant_connection(),
        "Environment Variables": test_environment_variables(),
        "Project Modules": test_project_imports(),
    }
    
    print_header("Test Summary")
    all_passed = True
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {test_name:30s} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("  ALL TESTS PASSED! [OK]")
        print("="*60)
        return 0
    else:
        print("  SOME TESTS FAILED [FAIL]")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
