import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class FileOwnerType(models.TextChoices):
    DOCUMENT = "DOCUMENT", _("Document")
    GALLERY_WORK = "GALLERY_WORK", _("Gallery work")
    OTHER = "OTHER", _("Other")


class FileObject(models.Model):
    """
    Generic file record that points to a Google Drive file (or other backends).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "subscriptions.Organization",
        on_delete=models.CASCADE,
        related_name="files",
        null=True,
        blank=True,
        help_text=_("Organization this file belongs to"),
    )
    owner_type = models.CharField(
        max_length=32,
        choices=FileOwnerType.choices,
        default=FileOwnerType.OTHER,
    )
    owner_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=_("ID of the related object (e.g. document, gallery work)"),
    )
    drive_file_id = models.CharField(max_length=255, db_index=True)
    drive_folder_id = models.CharField(max_length=255, blank=True)
    logical_path = models.CharField(
        max_length=512,
        blank=True,
        help_text=_("Logical path inside Drive, e.g. academy-crm/gallery/user-123"),
    )
    mime_type = models.CharField(max_length=255, blank=True)
    size = models.BigIntegerField(null=True, blank=True)
    original_name = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_files",
    )
    visibility = models.CharField(
        max_length=20,
        choices=[
            ("PRIVATE", _("Private")),
            ("ADMIN", _("Admin only")),
            ("PUBLIC", _("Public")),
        ],
        default="PRIVATE",
    )
    is_archived = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_files",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "storage_files"
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["owner_type", "owner_id"]),
            models.Index(fields=["is_archived", "deleted_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.original_name} ({self.drive_file_id})"


class FileActivity(models.Model):
    """
    Audit trail of file-related actions (upload, archive, restore, download).
    """

    ACTION_CHOICES = [
        ("uploaded", "Uploaded"),
        ("downloaded", "Downloaded"),
        ("archived", "Archived"),
        ("restored", "Restored"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(
        FileObject,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="file_activities",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "storage_file_activity"
        indexes = [
            models.Index(fields=["file"]),
            models.Index(fields=["user"]),
            models.Index(fields=["action", "timestamp"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.action} {self.file_id} by {self.user_id}"







