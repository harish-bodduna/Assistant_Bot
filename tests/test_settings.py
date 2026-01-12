import os

from config.settings import Settings, get_settings


def test_settings_defaults(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("AZURE_TENANT_ID", "t")
    monkeypatch.setenv("AZURE_CLIENT_ID", "c")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "s")
    monkeypatch.setenv("SHAREPOINT_SITE_ID", "site")
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    settings = get_settings()
    assert settings.qdrant_collection_visual == "tech_manuals"
    assert settings.qdrant_collection_text == "tech_manuals_text_only"

