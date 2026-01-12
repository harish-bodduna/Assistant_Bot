from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional

from docling.document_converter import DocumentConverter
from docling_core.types.io import DocumentStream
from docling_core.types.doc import PictureItem, TextItem

from .step_builder import detect_step_number


def parse_document(converter: DocumentConverter, pdf_bytes: bytes, file_name: str) -> tuple[Any, List[Dict[str, Any]]]:
    """Run docling conversion and return (doc, collected_items)."""
    ds = DocumentStream(name=file_name, stream=io.BytesIO(pdf_bytes))
    conv_res = converter.convert(ds)
    doc = conv_res.document
    if not doc:
        raise RuntimeError("Docling conversion returned no document")

    collected: List[Dict[str, Any]] = []
    for idx, (element, _level) in enumerate(doc.iterate_items()):
        if isinstance(element, TextItem):
            text = (element.text or "").strip()
            if not text:
                continue
            step_no = detect_step_number(text)
            collected.append({"idx": idx, "type": "text", "text": text, "step": step_no})
        elif isinstance(element, PictureItem):
            try:
                img = element.get_image(doc)
            except Exception:
                continue
            page_no = 0
            try:
                page_no = element.prov[0].page_no  # type: ignore[index]
            except Exception:
                page_no = 0
            collected.append({"idx": idx, "type": "image", "image": img, "page": page_no, "step": None})
    return doc, collected

