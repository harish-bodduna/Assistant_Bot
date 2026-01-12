from __future__ import annotations

import os
from typing import List, Optional, Tuple

from azure.storage.blob import BlobServiceClient


class RawFilesBlobReader:
    """
    Simple reader for Azure Blob 'raw-files' container.

    Layout assumption:
      raw-files/<doc_name_without_ext>/<file>.pdf
    Only PDF is supported; DOCX will be skipped/raise.
    """

    def __init__(self, container: str = "raw-files", connection_string: Optional[str] = None) -> None:
        conn = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not conn:
            raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is required to read raw-files")
        self.container = container
        self.service = BlobServiceClient.from_connection_string(conn)
        self.client = self.service.get_container_client(container)

    def list_documents(self) -> List[str]:
        """Return unique top-level folder names under the container."""
        docs = set()
        for blob in self.client.list_blobs():
            name = blob.name
            if "/" in name:
                prefix = name.split("/", 1)[0]
                if prefix:
                    docs.add(prefix)
        return sorted(docs)

    def fetch_pdf(self, doc_name: str) -> Tuple[bytes, str]:
        """
        Fetch the first PDF under raw-files/<doc_name>/.
        Skips DOCX (unsupported).
        """
        prefix = f"{doc_name}/"
        pdf_blob = None
        for blob in self.client.list_blobs(name_starts_with=prefix):
            if blob.name.lower().endswith(".pdf"):
                pdf_blob = blob.name
                break
            if blob.name.lower().endswith(".docx"):
                # DOCX not supported in this pipeline
                continue
        if not pdf_blob:
            raise FileNotFoundError(f"No PDF found for doc '{doc_name}' in container '{self.container}'")
        downloader = self.client.get_blob_client(pdf_blob)
        data = downloader.download_blob().readall()
        return data, pdf_blob

