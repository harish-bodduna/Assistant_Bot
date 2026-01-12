from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from datetime import datetime

from src.bridge.sharepoint_connector import SharePointConnector
from src.config.settings import get_settings
from src.text_indexing.layout_ingestor import LayoutAwareIngestor


def ts_print(msg: str) -> None:
    print(f"[{datetime.now().isoformat()}] {msg}")


def _save_pdf_to_local(pdf_bytes: bytes, pdf_name: str) -> Path:
    """
    Save PDF bytes to local source_docs folder.
    Returns the path where the file was saved.
    """
    source_docs_dir = Path("source_docs")
    source_docs_dir.mkdir(exist_ok=True)
    
    # Sanitize filename (keep it safe for filesystem)
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_", ".", " ") else "_" for ch in pdf_name)
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    
    file_path = source_docs_dir / safe_name
    
    # Write PDF bytes
    file_path.write_bytes(pdf_bytes)
    ts_print(f"Saved PDF to {file_path}")
    
    return file_path


def ingest_one(file_id: Optional[str] = None, folder_path: Optional[str] = "Shared Documents") -> Dict[str, Any]:
    """
    Thin wrapper to ingest a single PDF from SharePoint into Qdrant + Azure.
    Returns a status dict instead of raising.
    """
    ts_print(f"Starting ingest_one (folder={folder_path}, file_id={file_id})")
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
        target = next((f for f in files if (f.get("id") if isinstance(f, dict) else getattr(f, "id", None)) == file_id), None)
    else:
        target = next(
            (
                f
                for f in files
                if (
                    ((f.get("name") if isinstance(f, dict) else getattr(f, "name", None)) or "")
                    .lower()
                    .endswith(".pdf")
                )
            ),
            None,
        )
    if not target:
        ts_print("No PDF found in SharePoint folder.")
        return {"ok": False, "message": "No PDF found in SharePoint folder."}

    pdf_id = target.get("id") if isinstance(target, dict) else getattr(target, "id", None)
    pdf_name = target.get("name") if isinstance(target, dict) else getattr(target, "name", "manual.pdf")

    try:
        ts_print(f"Downloading {pdf_name} ({pdf_id})")
        pdf_bytes = sp.get_file_stream(pdf_id)
    except Exception as exc:
        ts_print(f"Download failed: {exc}")
        return {"ok": False, "message": f"Download failed: {exc}", "file": pdf_name}

    # Save PDF to local sourceDocs folder
    try:
        _save_pdf_to_local(pdf_bytes, pdf_name)
    except Exception as exc:
        ts_print(f"Warning: Failed to save PDF to local folder: {exc}")

    ingestor = LayoutAwareIngestor(collection="manuals_text")
    try:
        ts_print(f"Ingesting {pdf_name}")
        ingestor.index_pdf(pdf_bytes, file_name=pdf_name)
        ts_print(f"Ingested {pdf_name}")
        return {"ok": True, "message": f"Ingested {pdf_name}", "file": pdf_name}
    except Exception as exc:
        ts_print(f"Ingestion failed: {exc}")
        return {"ok": False, "message": f"Ingestion failed: {exc}", "file": pdf_name}


def ingest_all(folder_path: Optional[str] = "Shared Documents") -> Dict[str, Any]:
    """
    Thin wrapper to ingest all PDFs in a SharePoint folder.
    Returns a summary dict with counts.
    """
    ts_print(f"Starting ingest_all (folder={folder_path})")
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
        if (
            ((f.get("name") if isinstance(f, dict) else getattr(f, "name", None)) or "")
            .lower()
            .endswith(".pdf")
        )
    ]
    if not pdfs:
        ts_print("No PDFs found in SharePoint folder.")
        return {"ok": False, "message": "No PDFs found in SharePoint folder.", "processed": 0, "failed": 0}

    ingestor = LayoutAwareIngestor(collection="manuals_text")
    ok_count, fail_count = 0, 0
    errors = []
    for f in pdfs:
        pdf_id = f.get("id") if isinstance(f, dict) else getattr(f, "id", None)
        pdf_name = f.get("name") if isinstance(f, dict) else getattr(f, "name", "manual.pdf")
        try:
            ts_print(f"Downloading {pdf_name} ({pdf_id})")
            pdf_bytes = sp.get_file_stream(pdf_id)
            
            # Save PDF to local sourceDocs folder
            try:
                _save_pdf_to_local(pdf_bytes, pdf_name)
            except Exception as exc:
                ts_print(f"Warning: Failed to save PDF to local folder: {exc}")
            
            ts_print(f"Ingesting {pdf_name}")
            ingestor.index_pdf(pdf_bytes, file_name=pdf_name)
            ok_count += 1
        except Exception as exc:
            fail_count += 1
            errors.append(f"{pdf_name}: {exc}")
            ts_print(f"Failed {pdf_name}: {exc}")
    return {
        "ok": fail_count == 0,
        "message": f"Ingestion complete: {ok_count} succeeded, {fail_count} failed.",
        "processed": ok_count,
        "failed": fail_count,
        "errors": errors,
    }

