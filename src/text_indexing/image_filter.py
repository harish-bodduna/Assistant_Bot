from __future__ import annotations

import io
import os
from typing import List

import imagehash
from PIL import Image

from src.text_indexing.storage import AzureBlobStorage


def build_reference_hashes(ref_dir: str) -> List[imagehash.ImageHash]:
    """
    Build a list of reference hashes from images in a directory.
    These are used to filter out banned/icon images.
    Uses phash to match notebook logic.
    """
    ref_hashes: List[imagehash.ImageHash] = []
    valid_exts = (".png", ".jpg", ".jpeg")
    
    if not os.path.exists(ref_dir):
        return ref_hashes
    
    for filename in os.listdir(ref_dir):
        if filename.lower().endswith(valid_exts):
            path = os.path.join(ref_dir, filename)
            try:
                with Image.open(path) as img:
                    # Use phash to match notebook logic
                    h = imagehash.phash(img.convert("RGB"))
                    ref_hashes.append(h)
            except Exception:
                continue
    
    return ref_hashes


def capture_page_images(
    doc_result,
    storage: AzureBlobStorage,
    safe_base: str,
) -> dict:
    """
    Capture full page images from docling result and upload to blob storage.
    
    Returns:
        Dict mapping page_no -> SAS URL
    """
    page_sas_urls: dict = {}
    
    for page_no, page in doc_result.document.pages.items():
        if page.image:
            img_byte_arr = io.BytesIO()
            page.image.pil_image.save(img_byte_arr, format='PNG')
            
            blob_name = f"{safe_base}/pages/page_{page_no}.png"
            sas_url = storage.upload_and_get_sas(img_byte_arr.getvalue(), blob_name, days=365)
            page_sas_urls[page_no] = sas_url
    
    return page_sas_urls
