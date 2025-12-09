"""
Cloudinary service and helpers for Academy CRM.

This module centralizes all communication with Cloudinary API so that
apps like ``documents``, ``gallery``, and ``accounts`` can work with
a simple, backend-only abstraction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.conf import settings

logger = logging.getLogger(__name__)


def is_cloudinary_enabled() -> bool:
    """Return True if Cloudinary storage is enabled via settings."""
    # Check for CLOUDINARY_URL first (single variable format)
    cloudinary_url = getattr(settings, "CLOUDINARY_URL", None)
    if cloudinary_url:
        return True
    
    # Fall back to individual variables
    return bool(
        getattr(settings, "CLOUDINARY_CLOUD_NAME", None)
        and getattr(settings, "CLOUDINARY_API_KEY", None)
        and getattr(settings, "CLOUDINARY_API_SECRET", None)
    )


@lru_cache(maxsize=1)
def _configure_cloudinary():
    """
    Configure Cloudinary using settings.
    Supports both CLOUDINARY_URL (single variable) and individual variables.
    """
    if not is_cloudinary_enabled():
        raise RuntimeError("Cloudinary storage is not enabled or misconfigured.")

    # Check for CLOUDINARY_URL first (preferred format: cloudinary://api_key:api_secret@cloud_name)
    cloudinary_url = getattr(settings, "CLOUDINARY_URL", None)
    if cloudinary_url:
        cloudinary.config(
            cloudinary_url=cloudinary_url,
            secure=getattr(settings, "CLOUDINARY_SECURE", True),
        )
    else:
        # Fall back to individual variables
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=getattr(settings, "CLOUDINARY_SECURE", True),
        )


@dataclass
class UploadedFileInfo:
    """Information about an uploaded file."""
    public_id: str
    url: str
    secure_url: str
    resource_type: str
    format: str
    width: Optional[int]
    height: Optional[int]
    bytes: int
    folder: str


class CloudinaryService:
    """
    High-level wrapper around Cloudinary API used by the application.
    """

    def __init__(self):
        if not is_cloudinary_enabled():
            raise RuntimeError("Cloudinary storage is not enabled.")
        _configure_cloudinary()

    def upload_file(
        self,
        *,
        file_content,
        folder: str,
        public_id: Optional[str] = None,
        resource_type: str = "auto",
        overwrite: bool = True,
        invalidate: bool = True,
        **kwargs
    ) -> UploadedFileInfo:
        """
        Upload a file to Cloudinary.

        Args:
            file_content: File-like object or bytes to upload
            folder: Folder path in Cloudinary (e.g., "gallery/user-123")
            public_id: Optional public ID (filename without extension)
            resource_type: Type of resource (auto, image, video, raw)
            overwrite: Whether to overwrite existing files
            invalidate: Whether to invalidate CDN cache
            **kwargs: Additional Cloudinary upload options

        Returns:
            UploadedFileInfo with file details
        """
        upload_options = {
            "folder": folder,
            "resource_type": resource_type,
            "overwrite": overwrite,
            "invalidate": invalidate,
            **kwargs
        }

        if public_id:
            upload_options["public_id"] = public_id

        try:
            result = cloudinary.uploader.upload(
                file_content,
                **upload_options
            )

            return UploadedFileInfo(
                public_id=result.get("public_id", ""),
                url=result.get("url", ""),
                secure_url=result.get("secure_url", ""),
                resource_type=result.get("resource_type", "raw"),
                format=result.get("format", ""),
                width=result.get("width"),
                height=result.get("height"),
                bytes=result.get("bytes", 0),
                folder=folder,
            )
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            raise

    def delete_file(self, public_id: str, resource_type: str = "image") -> bool:
        """
        Delete a file from Cloudinary.

        Args:
            public_id: Public ID of the file to delete
            resource_type: Type of resource (image, video, raw)

        Returns:
            True if deleted successfully
        """
        try:
            result = cloudinary.uploader.destroy(
                public_id,
                resource_type=resource_type,
                invalidate=True
            )
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"Cloudinary delete failed for {public_id}: {e}")
            return False

    def get_file_url(
        self,
        public_id: str,
        transformation: Optional[str] = None,
        resource_type: str = "image",
        secure: bool = True
    ) -> str:
        """
        Get URL for a file with optional transformations.

        Args:
            public_id: Public ID of the file
            transformation: Cloudinary transformation string (e.g., "w_150,h_150,c_fill")
            resource_type: Type of resource (image, video, raw)
            secure: Whether to use HTTPS URL

        Returns:
            URL string
        """
        try:
            if transformation:
                url = cloudinary.CloudinaryImage(public_id).build_url(
                    transformation=transformation,
                    secure=secure
                )
            else:
                url = cloudinary.CloudinaryImage(public_id).build_url(secure=secure)

            return url
        except Exception as e:
            logger.error(f"Cloudinary URL generation failed for {public_id}: {e}")
            raise

    def move_file(self, public_id: str, from_folder: str = None, to_folder: str = None, resource_type: str = "image") -> bool:
        """
        Move a file from one folder to another in Cloudinary.

        Args:
            public_id: Public ID of the file (can include folder prefix or just filename)
            from_folder: Current folder path (optional, extracted from public_id if not provided)
            to_folder: Target folder path
            resource_type: Type of resource (image, video, raw) - must match the uploaded resource type

        Returns:
            True if moved successfully
        """
        try:
            # If public_id already includes folder, extract it
            if '/' in public_id:
                parts = public_id.split('/')
                filename = parts[-1]
                if from_folder is None:
                    from_folder = '/'.join(parts[:-1])
            else:
                filename = public_id
            
            # Build old and new public IDs
            if from_folder:
                old_public_id = f"{from_folder}/{filename}"
            else:
                old_public_id = filename
            
            if to_folder:
                new_public_id = f"{to_folder}/{filename}"
            else:
                new_public_id = filename

            result = cloudinary.uploader.rename(
                old_public_id,
                new_public_id,
                resource_type=resource_type,
                overwrite=True,
                invalidate=True
            )
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"Cloudinary move failed for {public_id}: {e}")
            return False

    def get_file_info(self, public_id: str, resource_type: str = "image") -> Optional[dict]:
        """
        Get file metadata from Cloudinary.

        Args:
            public_id: Public ID of the file
            resource_type: Type of resource (image, video, raw)

        Returns:
            Dictionary with file metadata or None if not found
        """
        try:
            result = cloudinary.api.resource(
                public_id,
                resource_type=resource_type
            )
            return result
        except Exception as e:
            logger.error(f"Cloudinary get info failed for {public_id}: {e}")
            return None


def get_cloudinary_service_or_none() -> Optional[CloudinaryService]:
    """
    Helper used by views/serializers: returns a Cloudinary service if enabled,
    otherwise ``None`` so callers can gracefully handle missing configuration.
    """
    if not is_cloudinary_enabled():
        return None
    try:
        return CloudinaryService()
    except Exception as exc:
        logger.error("Failed to initialize CloudinaryService: %s", exc)
        return None
