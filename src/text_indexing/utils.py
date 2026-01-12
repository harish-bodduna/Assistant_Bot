from __future__ import annotations

import re

IMG_RE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
URL_RE = re.compile(r"\bhttps?://\S+")


def strip_urls_for_embed(md: str) -> str:
    """Remove URLs and replace image markdown with just alt text for clean embeddings."""
    md = IMG_RE.sub(r"\1", md)
    md = URL_RE.sub("", md)
    return md

