"""
One-off helper script to migrate existing Document/Work files to Google Drive.

Usage (locally or on Render shell):
    python manage.py shell < scripts/migrate_files_to_drive.py

The script is idempotent: it only processes records without a file_object.
"""

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage

from academy_crm.google_drive import get_drive_service_or_none
from documents.models import Document
from gallery.models import Work
from storage.models import FileObject, FileOwnerType, FileActivity


def migrate_documents():
    drive = get_drive_service_or_none()
    if not drive:
        print("Google Drive is not configured; skipping documents migration.")
        return

    qs = Document.objects.filter(file_object__isnull=True).exclude(file="")
    print(f"Migrating {qs.count()} documents...")

    for doc in qs.iterator():
        file = doc.file
        if not file:
            continue

        with default_storage.open(file.name, "rb") as fh:
            path_segments = ["academy-crm", "documents", f"user-{doc.owner_id}"]
            folder_id = drive.ensure_folder_path(path_segments)
            uploaded = drive.upload_file(
                name=file.name.split("/")[-1],
                mime_type=file.file.content_type
                if hasattr(file.file, "content_type")
                else "application/octet-stream",
                content=fh,
                folder_id=folder_id,
            )

        file_obj = FileObject.objects.create(
            organization=doc.organization,
            owner_type=FileOwnerType.DOCUMENT,
            owner_id=doc.id,
            drive_file_id=uploaded.file_id,
            drive_folder_id=uploaded.folder_id,
            logical_path="/".join(path_segments),
            mime_type=uploaded.mime_type,
            size=uploaded.size,
            original_name=uploaded.name,
            created_by=doc.owner,
            visibility=doc.visibility,
        )
        doc.file_object = file_obj
        doc.save(update_fields=["file_object"])
        FileActivity.objects.create(
            file=file_obj,
            user=doc.owner,
            action="uploaded",
        )


def migrate_gallery():
    drive = get_drive_service_or_none()
    if not drive:
        print("Google Drive is not configured; skipping gallery migration.")
        return

    qs = Work.objects.filter(file_object__isnull=True).exclude(media="")
    print(f"Migrating {qs.count()} gallery works...")

    for work in qs.iterator():
        file = work.media
        if not file:
            continue

        with default_storage.open(file.name, "rb") as fh:
            path_segments = ["academy-crm", "gallery", f"user-{work.owner_id}"]
            folder_id = drive.ensure_folder_path(path_segments)
            uploaded = drive.upload_file(
                name=file.name.split("/")[-1],
                mime_type=file.file.content_type
                if hasattr(file.file, "content_type")
                else "application/octet-stream",
                content=fh,
                folder_id=folder_id,
            )

        file_obj = FileObject.objects.create(
            organization=work.organization,
            owner_type=FileOwnerType.GALLERY_WORK,
            owner_id=work.id,
            drive_file_id=uploaded.file_id,
            drive_folder_id=uploaded.folder_id,
            logical_path="/".join(path_segments),
            mime_type=uploaded.mime_type,
            size=uploaded.size,
            original_name=uploaded.name,
            created_by=work.owner,
            visibility="PUBLIC" if work.is_public else "PRIVATE",
        )
        work.file_object = file_obj
        work.save(update_fields=["file_object"])
        FileActivity.objects.create(
            file=file_obj,
            user=work.owner,
            action="uploaded",
        )


def main():
    migrate_documents()
    migrate_gallery()


if __name__ == "__main__":
    main()




