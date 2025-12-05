"""
Google Drive service and helpers for Academy CRM.

This module centralizes all communication with the Google Drive API so that
apps like ``documents`` and ``gallery`` can work with a simple, backend-only
abstraction instead of dealing with credentials directly.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, List, Optional, Tuple

from django.conf import settings

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

logger = logging.getLogger(__name__)


# Use drive scope (not drive.file) to access shared folders
# drive.file only allows access to files created by the service account
# drive allows access to all files the service account can access (including shared)
GOOGLE_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"


def is_drive_enabled() -> bool:
    """Return True if Google Drive storage is enabled via settings."""
    return bool(
        getattr(settings, "USE_GOOGLE_DRIVE_STORAGE", False)
        and settings.GOOGLE_DRIVE_CLIENT_EMAIL
        and settings.GOOGLE_DRIVE_PRIVATE_KEY
        and settings.GOOGLE_DRIVE_PROJECT_ID
        and settings.GOOGLE_DRIVE_ROOT_FOLDER_ID
    )


@lru_cache(maxsize=1)
def _build_drive_client():
    """
    Build and cache a Google Drive API client using service account credentials.
    """
    if not is_drive_enabled():
        raise RuntimeError("Google Drive storage is not enabled or misconfigured.")

    info = {
        "type": "service_account",
        "client_email": settings.GOOGLE_DRIVE_CLIENT_EMAIL,
        "private_key": settings.GOOGLE_DRIVE_PRIVATE_KEY,
        "token_uri": "https://oauth2.googleapis.com/token",
        "project_id": settings.GOOGLE_DRIVE_PROJECT_ID,
    }
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=[GOOGLE_DRIVE_SCOPE]
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


@dataclass
class UploadedFileInfo:
    file_id: str
    folder_id: str
    name: str
    mime_type: str
    size: Optional[int]


class GoogleDriveService:
    """
    High-level wrapper around Google Drive API used by the application.
    """

    def __init__(self):
        if not is_drive_enabled():
            raise RuntimeError("Google Drive storage is not enabled.")
        self.client = _build_drive_client()

    def verify_folder_access(self, folder_id: str) -> bool:
        """
        Verify that the service account can access the given folder.
        Returns True if accessible, False otherwise.
        Tries both personal Drive and Shared Drive access methods.
        """
        # Try without supportsAllDrives first (for personal Drive folders)
        try:
            self.client.files().get(
                fileId=folder_id,
                fields="id, name",
            ).execute()
            return True
        except Exception:
            # Try with supportsAllDrives (for Shared Drives)
            try:
                self.client.files().get(
                    fileId=folder_id,
                    fields="id, name",
                    supportsAllDrives=True,
                ).execute()
                return True
            except Exception as e:
                logger.warning(f"Cannot access folder {folder_id}: {e}")
                return False

    # Folder helpers -----------------------------------------------------
    def ensure_folder_path(
        self, path_segments: Iterable[str], root_folder_id: Optional[str] = None
    ) -> str:
        """
        Ensure that a nested folder path exists and return the final folder id.

        Example path: ['academy-crm', 'gallery', 'user-123']
        """
        root_id = root_folder_id or settings.GOOGLE_DRIVE_ROOT_FOLDER_ID
        
        # Verify root folder is accessible
        if not self.verify_folder_access(root_id):
            raise RuntimeError(
                f"Cannot access root folder {root_id}. "
                f"Please ensure the folder is shared with the service account "
                f"({settings.GOOGLE_DRIVE_CLIENT_EMAIL}) with 'Editor' permissions."
            )
        
        parent_id = root_id

        for segment in path_segments:
            segment = segment.strip().replace("/", "_")
            if not segment:
                continue

            # Build query - use 'user' corpora for personal Drive, 'allDrives' for Shared Drives
            # For personal Drive folders shared with service account, we need to search in user's drive
            query_params = {
                "q": (
                    f"mimeType = 'application/vnd.google-apps.folder' "
                    f"and name = '{segment}' "
                    f"and '{parent_id}' in parents "
                    f"and trashed = false"
                ),
                "spaces": "drive",
                "fields": "files(id, name)",
                "pageSize": 1,
            }
            
            # Try with user corpora first (for personal Drive), then fallback to allDrives (for Shared Drives)
            try:
                response = (
                    self.client.files()
                    .list(
                        **query_params,
                        corpora="user",
                        includeItemsFromAllDrives=False,
                    )
                    .execute()
                )
            except Exception:
                # Fallback to allDrives if user corpora doesn't work (for Shared Drives)
                response = (
                    self.client.files()
                    .list(
                        **query_params,
                        corpora="allDrives",
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                    )
                    .execute()
                )
            files = response.get("files", [])

            if files:
                parent_id = files[0]["id"]
                continue

            file_metadata = {
                "name": segment,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            created = (
                self.client.files()
                .create(
                    body=file_metadata,
                    fields="id, name",
                    supportsAllDrives=True,
                )
                .execute()
            )
            parent_id = created["id"]

        return parent_id

    # File operations ----------------------------------------------------
    def upload_file(
        self,
        *,
        name: str,
        mime_type: str,
        content: io.BytesIO,
        folder_id: str,
    ) -> UploadedFileInfo:
        # Ensure content is at the beginning
        if hasattr(content, 'seek'):
            content.seek(0)
        
        media = MediaIoBaseUpload(content, mimetype=mime_type, resumable=False)
        metadata = {"name": name, "parents": [folder_id]}
        
        # Try with supportsAllDrives first (for Shared Drives), then without (for personal Drive)
        try:
            file = (
                self.client.files()
                .create(
                    body=metadata,
                    media_body=media,
                    fields="id, name, mimeType, size",
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as e:
            # If that fails, try without supportsAllDrives (for personal Drive folders)
            logger.debug(f"Upload with supportsAllDrives failed, trying without: {e}")
            content.seek(0)  # Reset content pointer
            media = MediaIoBaseUpload(content, mimetype=mime_type, resumable=False)
            file = (
                self.client.files()
                .create(
                    body=metadata,
                    media_body=media,
                    fields="id, name, mimeType, size",
                )
                .execute()
            )
        
        return UploadedFileInfo(
            file_id=file["id"],
            folder_id=folder_id,
            name=file.get("name", name),
            mime_type=file.get("mimeType", mime_type),
            size=int(file["size"]) if "size" in file else None,
        )

    def move_file(self, file_id: str, new_parent_id: str) -> None:
        file = self.client.files().get(fileId=file_id, fields="parents").execute()
        previous_parents = ",".join(file.get("parents", []))
        self.client.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()

    def download_file(self, file_id: str) -> Tuple[bytes, str]:
        """
        Download file content and return (bytes, mime_type).
        """
        request = self.client.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logger.debug("Download %d%%.", int(status.progress() * 100))
        file = self.client.files().get(fileId=file_id, fields="mimeType").execute()
        fh.seek(0)
        return fh.read(), file.get("mimeType", "application/octet-stream")

    def get_file_metadata(self, file_id: str, fields: str = "id, name, mimeType, size"):
        return self.client.files().get(fileId=file_id, fields=fields).execute()

    def get_storage_quota(self) -> Optional[dict]:
        """
        Get storage quota information for the service account's Google Drive.
        Returns dict with 'limit', 'usage', 'usageInDrive', 'usageInDriveTrash' in bytes,
        or None if quota info is not available.
        """
        try:
            about = self.client.about().get(fields="storageQuota").execute()
            quota = about.get("storageQuota", {})
            if quota:
                return {
                    "limit": int(quota.get("limit", 0)) if quota.get("limit") else None,
                    "usage": int(quota.get("usage", 0)) if quota.get("usage") else 0,
                    "usageInDrive": int(quota.get("usageInDrive", 0)) if quota.get("usageInDrive") else 0,
                    "usageInDriveTrash": int(quota.get("usageInDriveTrash", 0)) if quota.get("usageInDriveTrash") else 0,
                }
            return None
        except Exception as e:
            logger.warning(f"Could not retrieve storage quota: {e}")
            return None


def get_drive_service_or_none() -> Optional[GoogleDriveService]:
    """
    Helper used by views/serializers: returns a drive service if enabled,
    otherwise ``None`` so callers can gracefully fall back to local storage.
    """
    if not is_drive_enabled():
        return None
    try:
        return GoogleDriveService()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to initialize GoogleDriveService: %s", exc)
        return None




