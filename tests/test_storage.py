import os

import pytest

from src.text_indexing.storage import AzureBlobStorage


def test_account_key_parses_from_conn_string(monkeypatch):
    conn = "DefaultEndpointsProtocol=https;AccountName=foo;AccountKey=MYKEY123;EndpointSuffix=core.windows.net"
    storage = AzureBlobStorage(container="dummy", connection_string=conn)
    assert storage._account_key() == "MYKEY123"

