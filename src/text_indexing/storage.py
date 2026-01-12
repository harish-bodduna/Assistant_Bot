from __future__ import annotations

import os
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas


class AzureBlobStorage:
    def __init__(self, container: str, connection_string: str) -> None:
        self.container = container
        self.connection_string = connection_string
        self.service = BlobServiceClient.from_connection_string(connection_string)
        self._ensure_container()

    def _ensure_container(self) -> None:
        try:
            self.service.create_container(self.container)
        except Exception:
            pass

    def upload_and_get_sas(self, data: bytes, blob_name: str, days: int = 30) -> str:
        blob_client = self.service.get_blob_client(container=self.container, blob=blob_name)
        blob_client.upload_blob(data, overwrite=True)
        account_name = self.service.account_name
        account_key = self._account_key()
        sas = generate_blob_sas(
            account_name=account_name,
            account_key=account_key,
            container_name=self.container,
            blob_name=blob_name,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(days=days),
            start=datetime.utcnow() - timedelta(minutes=5),
        )
        return (
            f"https://{self.service.account_name}.blob.core.windows.net/"
            f"{self.container}/{blob_name}?{sas}"
        )

    def _account_key(self) -> str:
        # 1) explicit env var
        env_key = os.getenv("AZURE_STORAGE_KEY")
        if env_key:
            return env_key
        # 2) parse from connection string
        for part in self.connection_string.split(";"):
            if part.lower().startswith("accountkey="):
                _, val = part.split("=", 1)
                if val:
                    return val
        # 3) credential attr fallback
        cred = getattr(self.service, "credential", None)
        cred_key = getattr(cred, "account_key", None)
        if cred_key:
            return cred_key
        raise RuntimeError("AZURE_STORAGE_KEY or AccountKey in connection string is required to sign SAS URLs")

