from __future__ import annotations

import io
import os
from typing import List

import fitz  # PyMuPDF
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


def get_enhanced_image(page, bbox, scale: float = 3.0) -> Image.Image:
    """
    Renders a specific area of a PDF page at a higher resolution.
    scale=3.0 effectively triples the DPI (e.g., from 72 to 216 DPI).
    
    Args:
        page: PyMuPDF page object
        bbox: Bounding box tuple (x0, y0, x1, y1) defining the area to extract
        scale: Scale factor for resolution enhancement (default 3.0)
        
    Returns:
        PIL Image of the enhanced/extracted region
    """
    # 1. Set the zoom/scale factor
    mat = fitz.Matrix(scale, scale)
    
    # 2. Render only the bounding box area of the image
    # We add a tiny 2-pixel padding to ensure no edges are cut off
    pix = page.get_pixmap(matrix=mat, clip=bbox, alpha=False)
    
    # 3. Convert to PIL Image
    img_data = pix.tobytes("png")
    return Image.open(io.BytesIO(img_data))


def capture_page_images(
    doc_result,
    storage: AzureBlobStorage,
    project_name: str,
) -> dict:
    """
    Capture full page images from docling result and upload to blob storage.
    Matches Document_parsing-2.ipynb structure: {project_name}/pages/page_{page_no}.png
    
    Args:
        doc_result: Docling conversion result
        storage: AzureBlobStorage instance
        project_name: Project name for blob path (e.g., "dummy")
        
    Returns:
        Dict mapping page_no (int) -> SAS URL
    """
    page_sas_urls: dict = {}
    
    for page_no, page in doc_result.document.pages.items():
        if page.image:
            img_byte_arr = io.BytesIO()
            page.image.pil_image.save(img_byte_arr, format='PNG')
            
            # Match notebook structure: {project_name}/pages/page_{page_no}.png
            blob_name = f"{project_name}/pages/page_{page_no}.png"
            sas_url = storage.upload_and_get_sas(img_byte_arr.getvalue(), blob_name, days=365)
            page_sas_urls[page_no] = sas_url
    
    return page_sas_urls
