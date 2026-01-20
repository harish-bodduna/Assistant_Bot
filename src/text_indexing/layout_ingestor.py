from __future__ import annotations

import io
import os
import secrets
import string
import time
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import imagehash
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.io import DocumentStream
from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.text_indexing.doc_parser import parse_document
from src.text_indexing.image_filter import build_reference_hashes, capture_page_images, get_enhanced_image
from src.text_indexing.qdrant_writer import upsert_markdown
from src.text_indexing.storage import AzureBlobStorage

# LlamaIndex embeddings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding


def ts_print(msg: str) -> None:
    """Timestamped stdout helper."""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def get_embed_model(force_hf: bool = True):
    """
    Choose an embedding model. Defaults to HF for local/dev; uses OpenAI if requested and key present.
    """
    if not force_hf:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                return OpenAIEmbedding(model="text-embedding-3-small", api_key=api_key)
            except Exception:
                pass
    return HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")


class LayoutAwareIngestor:
    """Use docling + PyMuPDF to process PDFs following Document_parsing-2.ipynb logic.
    
    Generates:
    - page_images: Full-page images (page maps) for structure inference
    - high_res_assets: Enhanced cropped images extracted via PyMuPDF
    - raw_text: Clean text for embedding/search
    """

    def __init__(self, collection: str = "manuals_text", banned_images_dir: Optional[str] = None) -> None:
        self.collection = collection
        self.embed = get_embed_model()
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            check_compatibility=False,
        )
        pipeline_options = PdfPipelineOptions()
        pipeline_options.generate_picture_images = True
        pipeline_options.images_scale = 2.0
        pipeline_options.generate_page_images = True
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.generate_parsed_pages = True
        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        self.blob_container = os.getenv("AZURE_STORAGE_CONTAINER", "qdrant-ingest-docs")
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not conn_str:
            raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is required for Azure blob uploads")
        self.storage = AzureBlobStorage(container=self.blob_container, connection_string=conn_str)
        
        # Build banned image hashes
        self.banned_hashes: list = []
        if banned_images_dir:
            self.banned_hashes = build_reference_hashes(banned_images_dir)
            ts_print(f"Loaded {len(self.banned_hashes)} banned image hashes from {banned_images_dir}")
        
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        dim = None
        if hasattr(self.embed, "get_text_embedding"):
            try:
                dim = len(self.embed.get_text_embedding("dummy"))
            except Exception:
                dim = None
        if dim is None:
            dim = getattr(self.embed, "dimensions", None) or getattr(self.embed, "dimension", None)
        if dim is None and hasattr(self.embed, "model") and hasattr(self.embed.model, "get_sentence_embedding_dimension"):
            dim = self.embed.model.get_sentence_embedding_dimension()
        if dim is None:
            raise RuntimeError("Embedding model did not expose dimensions")
        ts_print(f"Ensuring text collection '{self.collection}' (dim={dim})")
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            )

    def index_pdf(self, pdf_bytes: bytes, file_name: str) -> None:
        """Process PDF and generate 7 required outputs following notebook logic."""
        ts_print(f"Parsing {file_name} with component extraction")
        
        # Convert with docling to get conversion result
        ds = DocumentStream(name=file_name, stream=io.BytesIO(pdf_bytes))
        conv_res = self.converter.convert(ds)
        doc = conv_res.document
        
        if not doc:
            raise RuntimeError("Docling conversion returned no document")
        
        # Parse document structure (already filters images with phash)
        doc, collected = parse_document(
            doc,
            banned_hashes=self.banned_hashes,
            phash_threshold=15,
        )
        
        # Get safe base name for blob storage
        safe_base = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in Path(file_name).stem)
        project_name = os.getenv("AZURE_STORAGE_PROJECT_NAME", "dummy")
        document_folder = f"{project_name}/{safe_base}"
        storage_base_path = f"{project_name}/processed_images"
        
        # Capture page images from docling (matching notebook: project_name/pages/page_X.png)
        page_sas_urls = capture_page_images(conv_res, self.storage, document_folder)
        ts_print(f"Captured {len(page_sas_urls)} page images")
        
        # Get pages count
        pages_count = len(getattr(doc, "pages", {}) or {})
        
        # Get raw text from document (for embedding/search)
        raw_text_parts = []
        for item in collected:
            if item["type"] == "text":
                raw_text_parts.append(item["content"])
        raw_text = "\n".join(raw_text_parts)
        
        # Build LLM-ready markdown by iterating through collected items in order
        # Interleaves text and images as they appear in the document
        final_sas_markdown = []
        high_res_assets = []
        storage_base_path = f"{project_name}/processed_images"
        
        for item in collected:
            if item["type"] == "text":
                content = item["content"]
                final_sas_markdown.append(content)
            
            elif item["type"] == "image":
                pil_img = item["image"]
                page = item.get("page", 0)
                
                # Generate unique ID
                unique_hex = ''.join(secrets.choice(string.hexdigits.lower()) for _ in range(4))
                asset_id = f"ASSET_{unique_hex}"
                
                # Convert PIL image to bytes
                img_byte_arr = io.BytesIO()
                pil_img.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                # Upload to blob storage
                filename = f"visual_{unique_hex}_page_{page}.png"
                sas_url = self.storage.upload_and_get_sas(img_bytes, filename, storage_base_path, days=365)
                
                # Add markdown image syntax
                final_sas_markdown.append(f"![{unique_hex}]({sas_url})")
                
                # Track in high_res_assets for metadata
                high_res_assets.append({
                    "sas_url": sas_url,
                    "page": page,
                    "id": unique_hex,
                    "filename": filename
                })
        
        # Join with double newline to separate text and images
        llm_ready_sas_markdown = "\n\n".join(final_sas_markdown)
        
        ts_print(f"Built markdown with {len([i for i in collected if i['type'] == 'text'])} text blocks and {len(high_res_assets)} images")
        
        # Prepare payload matching Document_parsing-2 format
        payload = {
            "file_name": file_name,
            "page_images": page_sas_urls,  # Dict mapping page_no -> SAS URL (page maps)
            "high_res_assets": high_res_assets,  # List of {id, page, sas_url, filename}
            "pages_count": pages_count,
            "raw_text": raw_text,  # For embedding/search
            "llm_ready_sas_markdown": llm_ready_sas_markdown,
        }
        
        # Use raw_text for embedding (URL-free text)
        # Note: raw_text is passed separately to upsert_markdown as embed_markdown parameter
        # because it's used to generate the embedding vector (needs clean text without URLs).
        # The payload also contains raw_text (along with all 6 other fields) for storage and retrieval.
        # This design allows us to use clean text for embeddings while storing the full payload.
        upsert_markdown(self.client, self.collection, self.embed, raw_text, payload)
