from __future__ import annotations

import io
import os
import secrets
import string
import time
from pathlib import Path
from typing import Optional

import pytesseract
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.io import DocumentStream
from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.text_indexing.doc_parser import parse_document
from src.text_indexing.image_filter import build_reference_hashes, capture_page_images
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
    """Use docling to process PDFs and generate 7 required outputs following notebook logic."""

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
        self.blob_container = os.getenv("AZURE_STORAGE_CONTAINER", "dummy")
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
        # Note: We reuse self.converter from __init__ (created once and reused for efficiency),
        # but each PDF needs its own DocumentStream instance to process the PDF bytes
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
        storage_base_path = f"{project_name}/processed_images"
        
        # Capture page images from docling
        page_sas_urls = capture_page_images(conv_res, self.storage, safe_base)
        ts_print(f"Captured {len(page_sas_urls)} page images")
        
        # Get pages count
        pages_count = len(getattr(doc, "pages", {}) or {})
        
        # Get raw text from document (for embedding/search)
        raw_text_parts = []
        for item in collected:
            if item["type"] == "text":
                raw_text_parts.append(item["content"])
        raw_text = "\n".join(raw_text_parts)
        
        # Containers for both markdown versions
        ocr_structural_markdown = []  # Version A: OCR Placeholders for reasoning
        final_sas_markdown = []       # Version B: The SAS URL version
        asset_manifest_data = []      # The "Bridge" mapping table
        vision_sas_urls = []          # For the model's visual input
        
        # Process collected items in order
        for item in collected:
            if item["type"] == "text":
                content = item["content"]
                ocr_structural_markdown.append(f"[DOC_TEXT]: {content}")
                final_sas_markdown.append(content)
            
            elif item["type"] == "image":
                pil_img = item["image"]
                page = item.get("page", 0)
                
                # Generate the Shared ID
                unique_hex = ''.join(secrets.choice(string.hexdigits.lower()) for _ in range(4))
                asset_id = f"ASSET_{unique_hex}"
                
                # OCR Extraction
                try:
                    ocr_text = pytesseract.image_to_string(pil_img).strip().replace("\n", " ")
                except Exception:
                    ocr_text = "[No readable text found]"
                
                # Upload image and get SAS URL
                img_byte_arr = io.BytesIO()
                pil_img.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                filename = f"visual_{unique_hex}_page_{page}.png"
                blob_path = f"{storage_base_path}/{filename}"
                
                sas_url = self.storage.upload_and_get_sas(img_bytes, blob_path, days=365)
                
                # Populate Both Markdown Versions
                
                # A. The OCR Version
                img_placeholder = (
                    f"\n--- IMAGE OCR PLACEHOLDER ---\n"
                    f"SOURCE_ID: {asset_id}\n"
                    f"TEXT_FOUND_IN_IMAGE: {ocr_text}\n"
                    f"--- END OCR PLACEHOLDER ---\n"
                )
                ocr_structural_markdown.append(img_placeholder)
                
                # B. The SAS URL Version (Interleaved images with clickable links)
                final_sas_markdown.append(f"![Document Visual {unique_hex}]({sas_url})")
                
                # C. The Manifest dict
                asset_manifest_data.append({
                    "id": asset_id,
                    "ocr": ocr_text,
                    "url": sas_url
                })
                vision_sas_urls.append(sas_url)
        
        # Final Strings
        llm_reasoning_draft = "\n".join(ocr_structural_markdown)
        llm_ready_sas_markdown = "\n\n".join(final_sas_markdown)
        
        ts_print(f"Generated {len(asset_manifest_data)} image assets with OCR")
        ts_print(f"Generated {len(vision_sas_urls)} visual SAS URLs")
        
        # Prepare payload with all 7 required fields
        payload = {
            "file_name": file_name,
            "llm_reasoning_draft": llm_reasoning_draft,
            "llm_ready_sas_markdown": llm_ready_sas_markdown,
            "manifest": asset_manifest_data,
            "visual_sas_urls": vision_sas_urls,
            "page_images": page_sas_urls,  # Dict mapping page_no -> SAS URL
            "pages_count": pages_count,
            "raw_text": raw_text,  # For embedding/search
        }
        
        # Use raw_text for embedding (URL-free text)
        # Note: raw_text is passed separately to upsert_markdown as embed_markdown parameter
        # because it's used to generate the embedding vector (needs clean text without URLs).
        # The payload also contains raw_text (along with all 6 other fields) for storage and retrieval.
        # This design allows us to use clean text for embeddings while storing the full payload.
        upsert_markdown(self.client, self.collection, self.embed, raw_text, payload)
