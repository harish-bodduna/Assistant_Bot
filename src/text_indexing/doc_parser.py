from __future__ import annotations

from typing import Any, Dict, List

import imagehash
from docling_core.types.doc import PictureItem, TextItem


def parse_document(
    doc: Any,
    banned_hashes: List[imagehash.ImageHash] | None = None,
    phash_threshold: int = 15,
) -> tuple[Any, List[Dict[str, Any]]]:
    """
    Parse docling document and collect items in order, filtering images with perceptual hashing.
    
    Follows notebook logic exactly:
    - Iterates through doc.iterate_items() in order
    - Collects text items directly
    - Filters images using phash against banned reference list
    - Tracks seen hashes to avoid duplicates
    
    Args:
        doc: Docling document object (from converter.convert().document)
        banned_hashes: List of image hashes to filter out (logos/icons)
        phash_threshold: Perceptual hash threshold for matching (default 15)
    
    Returns:
        Tuple of (doc, collected_items) where collected_items is a list of dicts
        with keys: "type" ("text" or "image"), "content" (for text), "image" (for images), etc.
    """
    if banned_hashes is None:
        banned_hashes = []

    collected: List[Dict[str, Any]] = []
    seen_hashes = set()

    # Iterate items in the exact order they appear in the PDF
    for idx, (element, _level) in enumerate(doc.iterate_items()):
        if isinstance(element, TextItem):
            text = (element.text or "").strip()
            if text:
                collected.append({"type": "text", "content": text, "idx": idx})
        
        elif isinstance(element, PictureItem):
            if element.image and element.image.pil_image:
                pil_img = element.image.pil_image
                
                # Generate hash for filtering
                try:
                    curr_hash = imagehash.phash(pil_img)
                except Exception:
                    continue
                
                # Filter against BANNED_REF_LIST (Logos/Arrows/Icons)
                is_banned = any((curr_hash - ref) <= phash_threshold for ref in banned_hashes)
                
                if is_banned:
                    continue  # Skip banned image
                
                # Filter against duplicates within the same document
                is_duplicate = any((curr_hash - h) < phash_threshold for h in seen_hashes)
                if is_duplicate:
                    continue  # Skip duplicate
                
                # Add to seen hashes and collect the clean image
                seen_hashes.add(curr_hash)
                
                # Get page number and bbox
                page_no = 0
                bbox = None
                try:
                    if element.prov:
                        page_no = element.prov[0].page_no
                        bbox = element.prov[0].bbox
                except Exception:
                    pass
                
                collected.append({
                    "type": "image",
                    "image": pil_img,
                    "index": idx,
                    "page": page_no,
                    "bbox": bbox,
                })

    return doc, collected
