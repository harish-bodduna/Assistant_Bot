"""
Test QA functionality with MFA question.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

# Add project root to sys.path for imports
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.retrieval.multimodal_service import hybrid_search, get_1440_response

def main():
    query = "explain multi factor authentication steps ?"
    
    print("=" * 60)
    print(f"Question: {query}")
    print("=" * 60)
    
    print("\n[1] Retrieving context from Qdrant...")
    retrieved_context = hybrid_search(query)
    
    if not retrieved_context.get("text"):
        print("ERROR: No context found in Qdrant")
        return 1
    
    print(f"[2] Context retrieved. Mode: {retrieved_context.get('mode')}")
    print(f"[3] Generating answer with GPT-5.2...")
    
    answer = get_1440_response(query, retrieved_context)
    
    print("\n" + "=" * 60)
    print("ANSWER:")
    print("=" * 60)
    print(answer)
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
