"""Manually ingest MFA markdown into demo Qdrant (port 7333)."""
from pathlib import Path
import re
from qdrant_client import QdrantClient
from qdrant_client.http import models
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from src.config.settings import get_settings
from src.text_indexing.qdrant_writer import upsert_markdown


def ingest_mfa_demo(markdown_path: str = None):
    """
    Ingest the MFA markdown into demo Qdrant.
    
    Args:
        markdown_path: Optional path to markdown file. If not provided, uses:
            - First tries: markdown_exports/mfa_manual_edit/llm_ready_sas_markdown.md (manually edited)
            - Falls back to: validations/Explain_multifactor_authentication_steps_20260120_115026/answer.md
    """
    settings = get_settings()
    
    # Determine which markdown file to use
    if markdown_path:
        markdown_file = Path(markdown_path)
    else:
        # Try manually edited markdown first
        manual_edit_file = Path("markdown_exports/mfa_manual_edit/llm_ready_sas_markdown.md")
        if manual_edit_file.exists():
            markdown_file = manual_edit_file
            print(f"Using manually edited markdown: {markdown_file}")
        else:
            # Fall back to validation folder
            validations_dir = Path("validations")
            mfa_folder = "Explain_multifactor_authentication_steps_20260120_115026"
            markdown_file = validations_dir / mfa_folder / "answer.md"
            print(f"Using validation markdown: {markdown_file}")
    
    if not markdown_file.exists():
        print(f"Error: Markdown file not found at {markdown_file}")
        print("\nTo generate markdown from PDF, run:")
        print("  python tests/generate_mfa_markdown.py")
        return
    
    mfa_markdown = markdown_file.read_text(encoding="utf-8")
    print(f"Loaded MFA markdown from {answer_file}")
    print(f"Markdown length: {len(mfa_markdown)} characters")
    
    # Connect to demo Qdrant
    try:
        demo_client = QdrantClient(
            url=settings.demo_qdrant_url,
            api_key=settings.demo_qdrant_api_key,
            check_compatibility=False,
        )
        print(f"Connected to demo Qdrant at {settings.demo_qdrant_url}")
    except Exception as e:
        print(f"Error connecting to demo Qdrant: {e}")
        return
    
    # Get embedding model
    embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Ensure collection exists
    collection = "manuals_text"
    dim = len(embed_model.get_text_embedding("dummy"))
    
    try:
        if not demo_client.collection_exists(collection):
            demo_client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            )
            print(f"Created collection '{collection}' in demo Qdrant (dim={dim})")
        else:
            print(f"Collection '{collection}' already exists in demo Qdrant")
    except Exception as e:
        print(f"Error ensuring collection: {e}")
        return
    
    # Extract text for embedding (remove markdown images for clean embedding)
    # Remove image markdown syntax for embedding text
    raw_text = re.sub(r'!\[.*?\]\(.*?\)', '', mfa_markdown)
    raw_text = re.sub(r'\n+', '\n', raw_text).strip()
    print(f"Extracted raw text for embedding: {len(raw_text)} characters")
    
    # Prepare payload matching the expected structure
    payload = {
        "file_name": "1440-Microsoft_Multifactor_Authentication_Documentation.pdf",
        "page_images": {},  # Empty for manual ingestion
        "high_res_assets": [],  # Empty for manual ingestion
        "pages_count": 0,  # Not applicable for manual markdown
        "raw_text": raw_text,
        "llm_ready_sas_markdown": mfa_markdown,  # This is what retrieval will use
    }
    
    # Upsert to demo Qdrant
    try:
        upsert_markdown(demo_client, collection, embed_model, raw_text, payload)
        print(f"Successfully ingested MFA markdown into demo Qdrant ({settings.demo_qdrant_url})")
        print(f"Collection: {collection}")
        print(f"Markdown length: {len(mfa_markdown)} characters")
    except Exception as e:
        print(f"Error ingesting markdown: {e}")
        return


if __name__ == "__main__":
    ingest_mfa_demo()
