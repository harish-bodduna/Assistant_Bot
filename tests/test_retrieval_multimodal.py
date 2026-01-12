import pytest

from src.retrieval.multimodal_service import _interleave_markdown_content


def test_interleave_limits_images_and_keeps_text():
    md = "Step text\n![a](http://x/1.png)\nMore\n![b](http://x/2.png)\nTail"
    result = _interleave_markdown_content(md, max_images=1)
    assert len([c for c in result if c["type"] == "image_url"]) == 1
    assert any("Step text" in c.get("text", "") for c in result if c["type"] == "text")


def test_interleave_uses_sas_urls_when_missing_images():
    md = "No images here."
    sas = ["http://sas1", "http://sas2"]
    result = _interleave_markdown_content(md, sas_urls=sas, max_images=5)
    imgs = [c for c in result if c["type"] == "image_url"]
    assert len(imgs) == len(sas)


