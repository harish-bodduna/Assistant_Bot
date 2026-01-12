from __future__ import annotations

import argparse
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.bridge.sharepoint_connector import SharePointConnector
from src.config.settings import get_settings
from src.text_indexing.doc_parser import parse_document
from src.text_indexing.markdown_builder import render_markdown, write_outputs
from src.text_indexing.qdrant_writer import upsert_markdown
from src.text_indexing.step_builder import build_steps
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
    """Use docling to convert PDF to markdown with inline image placeholders, store single doc."""

    def __init__(self, collection: str = "manuals_text") -> None:
        self.collection = collection
        self.embed = get_embed_model()
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            check_compatibility=False,
        )
        pipeline_options = PdfPipelineOptions()
        pipeline_options.generate_picture_images = True  # extract UI crops
        pipeline_options.images_scale = 2.0  # high quality crops
        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        self.blob_container = os.getenv("AZURE_STORAGE_CONTAINER", "manual-images")
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not conn_str:
            raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is required for Azure blob uploads")
        self.storage = AzureBlobStorage(container=self.blob_container, connection_string=conn_str)
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
        ts_print(f"Parsing {file_name} with component extraction")
        doc, collected = parse_document(self.converter, pdf_bytes, file_name)

        # Prepare per-document export folder
        safe_base = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in Path(file_name).stem)
        export_root = Path("markdown_exports")
        doc_dir = export_root / safe_base
        fig_dir = doc_dir / "images"
        if doc_dir.exists():
            shutil.rmtree(doc_dir)
        fig_dir.mkdir(parents=True, exist_ok=True)

        try:
            ordered_steps = build_steps(collected)
            full_markdown, embed_markdown, sas_urls, fig_meta = render_markdown(
                ordered_steps=ordered_steps,
                safe_base=safe_base,
                fig_dir=fig_dir,
                storage=self.storage,
            )
            md_output_path, md_sas, meta_sas = write_outputs(
                doc_dir=doc_dir,
                full_markdown=full_markdown,
                embed_markdown=embed_markdown,
                file_name=file_name,
                sas_urls=sas_urls,
                fig_meta=fig_meta,
                storage=self.storage,
            )
            ts_print(
                f"Wrote markdown to {md_output_path} with {len(fig_meta)} figures and {len(sas_urls)} SAS URLs"
            )

            payload = {
                "file_name": file_name,
                "total_pages": len(getattr(doc, "pages", []) or []),
                "text": embed_markdown,  # URL-free for embeddings
                "llm_markdown": full_markdown,  # SAS-ready for LLM context
                "sas_urls": sas_urls,
                "fig_images": fig_meta,
                "markdown_path": str(md_output_path),
                "markdown_sas": md_sas,
                "metadata_sas": meta_sas,
                "doc_type": "markdown_bridge",
            }
            upsert_markdown(self.client, self.collection, self.embed, embed_markdown, payload)
        except Exception as exc:
            ts_print(f"Ingestion failed for {file_name}: {exc}")
            raise


def ingest_one_pdf(file_id: Optional[str] = None, folder_path: Optional[str] = "Shared Documents") -> None:
    settings = get_settings()
    sp = SharePointConnector(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        site_id=settings.sharepoint_site_id,
        drive_id=settings.sharepoint_drive_id,
    )
    files = sp.list_files(folder_path=folder_path or settings.sharepoint_folder_path or "Documents")
    target = None
    if file_id:
        for f in files:
            fid = f.get("id") if isinstance(f, dict) else getattr(f, "id", None)
            if fid == file_id:
                target = f
                break
    else:
        # pick first PDF
        for f in files:
            name = f.get("name") if isinstance(f, dict) else getattr(f, "name", "") or ""
            if name.lower().endswith(".pdf"):
                target = f
                break
    if not target:
        raise RuntimeError("No PDF found in SharePoint folder.")

    pdf_id = target.get("id") if isinstance(target, dict) else getattr(target, "id", None)
    pdf_name = target.get("name") if isinstance(target, dict) else getattr(target, "name", "manual.pdf")
    ts_print(f"Selected PDF {pdf_name} ({pdf_id})")
    try:
        pdf_bytes = sp.get_file_stream(pdf_id)
    except Exception as exc:
        ts_print(f"Failed to download PDF: {exc}")
        return

    ingestor = LayoutAwareIngestor(collection="manuals_text")
    try:
        ingestor.index_pdf(pdf_bytes, file_name=pdf_name)
        ts_print("Ingestion complete.")
    except Exception as exc:
        ts_print(f"Ingestion failed: {exc}")


def ingest_all_pdfs(folder_path: Optional[str] = "Shared Documents") -> None:
    """Ingest all PDFs in the given folder using the layout-aware pipeline."""
    settings = get_settings()
    sp = SharePointConnector(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        site_id=settings.sharepoint_site_id,
        drive_id=settings.sharepoint_drive_id,
    )
    files = sp.list_files(folder_path=folder_path or settings.sharepoint_folder_path or "Documents")
    pdfs = [
        f
        for f in files
        if (f.get("name") if isinstance(f, dict) else getattr(f, "name", "") or "").lower().endswith(".pdf")
    ]
    if not pdfs:
        raise RuntimeError("No PDFs found in SharePoint folder.")

    ingestor = LayoutAwareIngestor(collection="manuals_text")

    for f in pdfs:
        pdf_id = f.get("id") if isinstance(f, dict) else getattr(f, "id", None)
        pdf_name = f.get("name") if isinstance(f, dict) else getattr(f, "name", "manual.pdf")
        ts_print(f"Selected PDF {pdf_name} ({pdf_id})")
        try:
            pdf_bytes = sp.get_file_stream(pdf_id)
            ingestor.index_pdf(pdf_bytes, file_name=pdf_name)
        except Exception as exc:
            ts_print(f"Skipping {pdf_name} due to error: {exc}")
    ts_print(f"Ingestion complete for {len(pdfs)} PDF(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest PDFs from SharePoint")
    parser.add_argument("folder", nargs="?", default="Shared Documents", help="Folder path in SharePoint")
    parser.add_argument("--file-id", dest="file_id", help="Specific file ID to ingest")
    parser.add_argument("--all", dest="ingest_all", action="store_true", help="Ingest all PDFs in folder")
    args = parser.parse_args()

    start = time.time()
    if args.ingest_all:
        ingest_all_pdfs(folder_path=args.folder)
    else:
        ingest_one_pdf(file_id=args.file_id, folder_path=args.folder)
    ts_print(f"Done in {time.time() - start:.2f}s")

