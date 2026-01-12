from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional

import requests
from azure.identity import ClientSecretCredential
from loguru import logger
from msgraph import GraphServiceClient

from src.config.settings import get_settings


class SharePointConnector:
    """
    SharePoint bridge using Microsoft Graph.

    - Auth via azure-identity ClientSecretCredential.
    - Provides file streaming and listing with detailed logging.
    - Supports resolving a drive by name (e.g., "Documents").
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        site_id: str,
        drive_id: Optional[str] = None,
        drive_name: str = "Documents",
    ) -> None:
        self.site_id = site_id
        self.drive_id = drive_id
        self.drive_name = drive_name

        scopes = ["https://graph.microsoft.com/.default"]
        credential = ClientSecretCredential(
            tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
        )
        self.credential = credential
        self.client = GraphServiceClient(credential, scopes=scopes)
        logger.debug(
            "Initialized GraphServiceClient site_id={} drive_id={} drive_name={}",
            site_id,
            drive_id,
            drive_name,
        )

    def _token(self) -> str:
        return self.credential.get_token("https://graph.microsoft.com/.default").token

    @lru_cache(maxsize=1)
    def _default_drive_id(self) -> str:
        """Resolve default drive id for the site if none was provided."""
        logger.debug("Resolving default drive ID for site_id={}", self.site_id)
        token = self._token()
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drives",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        drives = resp.json().get("value", []) or []
        if not drives:
            raise RuntimeError("No drives found for site")
        # Prefer Documents drive
        drive = next((d for d in drives if d.get("name") == "Documents"), drives[0])
        drive_id = drive.get("id")
        if not drive_id:
            raise RuntimeError("Unable to resolve default drive ID for site")
        logger.debug("Resolved default drive_id={}", drive_id)
        return drive_id

    @lru_cache(maxsize=1)
    def _drive_id_from_name(self) -> Optional[str]:
        """Resolve drive ID by its friendly name."""
        logger.debug("Resolving drive by name='{}' for site_id={}", self.drive_name, self.site_id)
        token = self._token()
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drives",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        drives = resp.json().get("value", []) or []
        for d in drives:
            if d.get("name") == self.drive_name:
                found = d.get("id")
                logger.debug("Resolved drive '{}' to id={}", self.drive_name, found)
                return found
        return None

    def _resolved_drive_id(self) -> str:
        if self.drive_id and len(self.drive_id) > 10:
            return self.drive_id
        return self._drive_id_from_name() or self._default_drive_id()

    def get_file_stream(self, file_id: str) -> bytes:
        """Fetch the raw byte stream of a file (typically PDF) from SharePoint."""
        drive_id = self._resolved_drive_id()
        logger.debug(
            "Fetching file stream from Graph",
            extra={"site_id": self.site_id, "drive_id": drive_id, "file_id": file_id},
        )
        token = self._token()
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/content"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        data = resp.content
        logger.debug("Retrieved file stream length={} bytes", len(data))
        return data

    def get_file_stream_by_path(self, path: str) -> bytes:
        """
        Fetch bytes for an item by path (e.g., 'Documents/MyFolder/foo.pdf').
        """
        drive_id = self._resolved_drive_id()
        logger.debug(
            "Fetching file stream by path",
            extra={"site_id": self.site_id, "drive_id": drive_id, "path": path},
        )
        token = self._token()
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{path}:/content"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        data = resp.content
        logger.debug("Retrieved file stream length={} bytes", len(data))
        return data  # type: ignore[return-value]

    def list_files(self, folder_path: str = "Documents") -> List[Dict]:
        """
        List files in a folder path. Returns ID, name, lastModified.
        """
        drive_id = self._resolved_drive_id()
        logger.debug(
            "Listing files",
            extra={"site_id": self.site_id, "drive_id": drive_id, "folder_path": folder_path},
        )
        clean_path = folder_path or ""
        if clean_path.lower() in ("", "root", "/", "documents", "shared documents"):
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
        else:
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{clean_path}:/children"
        token = self._token()
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        items = resp.json().get("value", []) or []
        result = []
        for child in items:
            if isinstance(child, dict):
                cid = child.get("id")
                name = child.get("name")
                last = child.get("lastModifiedDateTime") or child.get("lastModified")
            else:
                cid = getattr(child, "id", None)
                name = getattr(child, "name", None)
                last = getattr(child, "last_modified_date_time", None)
            result.append({"id": cid, "name": name, "lastModified": last})
        logger.debug("Listed {} items from folder {}", len(result), folder_path)
        return result

    def get_first_pdf_in_folder(self, folder_path: str = "Documents") -> bytes:
        """
        Convenience: fetch the first PDF bytes in a folder.
        Raises FileNotFoundError if none exist.
        """
        files = self.list_files(folder_path=folder_path)
        pdf = next((f for f in files if (f.get("name") or "").lower().endswith(".pdf")), None)
        if not pdf:
            raise FileNotFoundError(f"No PDF found in folder '{folder_path}'")
        file_id = pdf.get("id")
        return self.get_file_stream(file_id)  # type: ignore[arg-type]


if __name__ == "__main__":
    """
    Mock/test block.

    Requires env vars:
      - AZURE_TENANT_ID
      - AZURE_CLIENT_ID
      - AZURE_CLIENT_SECRET
      - SHAREPOINT_SITE_ID
      - (optional) SHAREPOINT_DRIVE_ID
      - (optional) SHAREPOINT_FOLDER_PATH
    """

    settings = get_settings()
    connector = SharePointConnector(
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        site_id=settings.sharepoint_site_id,
        drive_id=settings.sharepoint_drive_id,
    )

    try:
        folder = settings.sharepoint_folder_path or "Documents"
        files = connector.list_files(folder_path=folder)
        logger.info("Found {} files in folder {}", len(files), folder)
        for f in files:
            logger.info(f)
    except Exception as exc:  # pragma: no cover - network call
        logger.error("SharePoint mock run failed: {}", exc)

