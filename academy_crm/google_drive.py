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
        parent_id = root_id
        
        # Note: We skip strict folder verification because:
        # 1. For personal Drive folders shared with service accounts, files().get() may fail
        # 2. But files().create() and files().list() will work if properly shared
        # 3. If access fails, it will be caught when we try to list/create folders with better error messages

        for segment in path_segments:
            # Log which folder we're looking for
            logger.debug(f"Looking for folder '{segment}' in parent folder {parent_id}")
            segment = segment.strip().replace("/", "_")
            if not segment:
                continue

            # Build query - escape single quotes in segment name to prevent injection
            escaped_segment = segment.replace("'", "\\'")
            query_params = {
                "q": (
                    f"mimeType = 'application/vnd.google-apps.folder' "
                    f"and name = '{escaped_segment}' "
                    f"and '{parent_id}' in parents "
                    f"and trashed = false"
                ),
                "spaces": "drive",
                "fields": "files(id, name)",
                "pageSize": 1,
            }
            
            # Try multiple query methods to find the folder
            files = []
            last_error = None
            
            # Method 1: Try with user corpora (for personal Drive)
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
                files = response.get("files", [])
                if files:
                    logger.debug(f"Found folder '{segment}' using corpora='user'")
            except Exception as e:
                last_error = e
                logger.debug(f"Query with corpora='user' failed: {e}")
            
            # Method 2: Try without corpora (default - searches all accessible files including shared)
            if not files:
                try:
                    # Remove corpora restriction to search all accessible files
                    # This works for personal Drive folders shared with service accounts
                    response = (
                        self.client.files()
                        .list(
                            q=query_params["q"],
                            spaces="drive",
                            fields="files(id, name)",
                            pageSize=1,
                        )
                        .execute()
                    )
                    files = response.get("files", [])
                    if files:
                        logger.debug(f"Found folder '{segment}' using default query (no corpora)")
                except Exception as e:
                    last_error = e
                    logger.debug(f"Default query failed: {e}")
            
            # Method 2.5: Try searching in shared files explicitly
            if not files:
                try:
                    # Search for files shared with the service account
                    response = (
                        self.client.files()
                        .list(
                            q=(
                                f"mimeType = 'application/vnd.google-apps.folder' "
                                f"and name = '{escaped_segment}' "
                                f"and '{parent_id}' in parents "
                                f"and trashed = false "
                                f"and sharedWithMe = true"
                            ),
                            spaces="drive",
                            fields="files(id, name)",
                            pageSize=1,
                        )
                        .execute()
                    )
                    files = response.get("files", [])
                    if files:
                        logger.debug(f"Found folder '{segment}' using sharedWithMe query")
                except Exception as e:
                    last_error = e
                    logger.debug(f"sharedWithMe query failed: {e}")
            
            # Method 3: Try with allDrives (for Shared Drives)
            if not files:
                try:
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
                        logger.debug(f"Found folder '{segment}' using corpora='allDrives'")
                except Exception as e:
                    last_error = e
                    logger.debug(f"Query with corpora='allDrives' failed: {e}")
            
            # Log if we couldn't find the folder
            if not files:
                logger.warning(
                    f"Could not find folder '{segment}' in parent {parent_id}. "
                    f"Will create new folder. Last error: {last_error}"
                )

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




