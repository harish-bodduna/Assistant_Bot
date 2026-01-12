from src.text_indexing.utils import strip_urls_for_embed


def test_strip_urls_for_embed_removes_urls():
    text = "See https://example.com/page and also http://foo.bar."
    out = strip_urls_for_embed(text)
    assert "http" not in out

