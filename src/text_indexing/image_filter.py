from __future__ import annotations

import io
import os
import secrets
import string
from pathlib import Path
from typing import List, Optional

import imagehash
import fitz  # PyMuPDF
from PIL import Image

from src.text_indexing.storage import AzureBlobStorage


def build_reference_hashes(ref_dir: str) -> List[imagehash.ImageHash]:
    """
    Build a list of reference hashes from images in a directory.
    These are used to filter out banned/icon images.
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
                    # Use dhash for icons/symbols
                    h = imagehash.dhash(img.convert("RGB"))
                    ref_hashes.append(h)
            except Exception:
                continue
    
    return ref_hashes


def get_enhanced_image(page: fitz.Page, bbox: fitz.Rect, scale: float = 3.0) -> Image.Image:
    """
    Render a specific area of a PDF page at higher resolution.
    scale=3.0 effectively triples the DPI (e.g., from 72 to 216 DPI).
    """
    mat = fitz.Matrix(scale, scale)
    # Add tiny padding to ensure no edges are cut off
    pix = page.get_pixmap(matrix=mat, clip=bbox, alpha=False)
    img_data = pix.tobytes("png")
    return Image.open(io.BytesIO(img_data))


def extract_and_filter_images(
    pdf_bytes: bytes,
    pdf_path: Optional[str] = None,
    banned_hashes: Optional[List[imagehash.ImageHash]] = None,
    threshold: int = 5,
    scale_factor: float = 3.0,
) -> List[dict]:
    """
    Extract all images from PDF using fitz, filter banned ones, return clean list.
    
    Returns:
        List of dicts with keys: 'image' (PIL Image), 'page' (int), 'id' (str), 'bbox' (tuple)
    """
    if banned_hashes is None:
        banned_hashes = []
    
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    clean_images: List[dict] = []
    
    for p_idx in range(len(doc)):
        page = doc.load_page(p_idx)
        for img_info in page.get_image_info():
            bbox = img_info["bbox"]
            
            # Convert to PIL for filtering
            try:
                pil_img = get_enhanced_image(page, bbox, scale=scale_factor)
            except Exception:
                continue
            
            # Check against banned hashes
            curr_hash = imagehash.phash(pil_img)
            is_match = any((curr_hash - ref) <= threshold for ref in banned_hashes)
            if is_match:
                continue  # Skip banned image
            
            # Generate unique ID
            image_idx = ''.join(secrets.choice(string.hexdigits.lower()) for _ in range(4))
            
            clean_images.append({
                "image": pil_img,
                "page": p_idx + 1,
                "id": image_idx,
                "bbox": bbox,
            })
    
    doc.close()
    return clean_images


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
