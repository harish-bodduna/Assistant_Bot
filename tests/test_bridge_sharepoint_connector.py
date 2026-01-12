import pytest

from src.bridge.sharepoint_connector import SharePointConnector


def test_resolved_drive_id_prefers_explicit_id(monkeypatch):
    conn = SharePointConnector(
        tenant_id="t",
        client_id="c",
        client_secret="s",
        site_id="site",
        drive_id="explicit_drive",
    )
    assert conn._resolved_drive_id() == "explicit_drive"


