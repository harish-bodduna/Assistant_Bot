from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .step_builder import detect_step_number  # re-exported for convenience
from .storage import AzureBlobStorage
from .step_builder import build_steps
from .utils import strip_urls_for_embed


def render_markdown(
    ordered_steps: List[Tuple[int, Dict[str, List[Dict[str, Any]]]]],
    safe_base: str,
    fig_dir: Path,
    storage: AzureBlobStorage,
    clean_images: Optional[List[Dict[str, Any]]] = None,  # NEW parameter
) -> tuple[str, str, List[str], List[Dict[str, Any]]]:
    md_parts: List[str] = []
    sas_urls: List[str] = []
    fig_meta: List[Dict[str, Any]] = []
    fig_counters: Dict[int, int] = {}

    for step_no, data in ordered_steps:
        content = data.get("content") or []
        texts_for_title = [c["text"] for c in content if c.get("type") == "text"]
        title = texts_for_title[0].split("\n")[0].strip() if texts_for_title else f"Step {step_no}"

        md_parts.append(f"### Step {step_no}: {title}")

        for itm in content:
            if itm["type"] == "text":
                md_parts.append(itm["text"])
            elif itm["type"] == "image":
                img = itm["image"]
                page_no = itm.get("page", 0) or 0
                fig_counters[step_no] = fig_counters.get(step_no, 0) + 1
                fig_idx = fig_counters[step_no]
                blob_name = f"{safe_base}/images/fig_{fig_idx}_page_{page_no}.png"
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                sas_url = storage.upload_and_get_sas(buf.getvalue(), blob_name)
                sas_urls.append(sas_url)

                local_name = f"fig_{fig_idx}_page_{page_no}.png"
                local_path = fig_dir / local_name
                img.save(local_path)

                md_parts.append(f"![Step {step_no} Visual]({sas_url})")
                fig_meta.append(
                    {
                        "step": step_no,
                        "page_number": page_no,
                        "sas_url": sas_url,
                        "local_path": str(local_path.resolve()),
                        "blob_name": blob_name,
                    }
                )

        md_parts.append("---")

    # NEW: Add clean images metadata (these are already uploaded, just reference them)
    if clean_images:
        for img_data in clean_images:
            sas_url = img_data.get("sas_url")
            if sas_url:
                sas_urls.append(sas_url)
                fig_meta.append({
                    "step": None,  # Not associated with a specific step
                    "page_number": img_data.get("page", 0),
                    "sas_url": sas_url,
                    "local_path": None,
                    "blob_name": img_data.get("filename", ""),
                    "id": img_data.get("id"),
                    "type": "clean_image",  # Mark as clean image
                })

    full_markdown = "\n\n".join(part for part in md_parts if part).strip()
    embed_markdown = strip_urls_for_embed(full_markdown)
    return full_markdown, embed_markdown, sas_urls, fig_meta


def write_outputs(
    doc_dir: Path,
    full_markdown: str,
    embed_markdown: str,
    file_name: str,
    sas_urls: List[str],
    fig_meta: List[Dict[str, Any]],
    storage: AzureBlobStorage,
):
    md_output_path = doc_dir / "markdown.md"
    md_output_path.write_text(full_markdown, encoding="utf-8")
    meta_path = doc_dir / "metadata.json"
    preamble: List[str] = []
    meta_path.write_text(
        json.dumps(
            {"file_name": file_name, "sas_urls": sas_urls, "figures": fig_meta, "preamble": preamble},
            indent=2,
        ),
        encoding="utf-8",
    )
    md_sas = storage.upload_and_get_sas(md_output_path.read_bytes(), f"{doc_dir.name}/markdown.md")
    meta_sas = storage.upload_and_get_sas(meta_path.read_bytes(), f"{doc_dir.name}/metadata.json")
    return md_output_path, md_sas, meta_sas

