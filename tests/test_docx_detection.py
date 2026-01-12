from visual_indexing.pipeline import _is_docx


def test_is_docx_detects_zip_magic():
    assert _is_docx(b"PK\x03\x04")
    assert not _is_docx(b"%PDF-1.7")

