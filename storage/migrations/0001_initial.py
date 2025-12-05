import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("subscriptions", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FileObject",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "owner_type",
                    models.CharField(
                        choices=[
                            ("DOCUMENT", "Document"),
                            ("GALLERY_WORK", "Gallery work"),
                            ("OTHER", "Other"),
                        ],
                        default="OTHER",
                        max_length=32,
                    ),
                ),
                (
                    "owner_id",
                    models.UUIDField(
                        blank=True,
                        help_text="ID of the related object (e.g. document, gallery work)",
                        null=True,
                    ),
                ),
                ("drive_file_id", models.CharField(max_length=255, db_index=True)),
                ("drive_folder_id", models.CharField(blank=True, max_length=255)),
                (
                    "logical_path",
                    models.CharField(
                        blank=True,
                        help_text="Logical path inside Drive, e.g. academy-crm/gallery/user-123",
                        max_length=512,
                    ),
                ),
                ("mime_type", models.CharField(blank=True, max_length=255)),
                ("size", models.BigIntegerField(blank=True, null=True)),
                ("original_name", models.CharField(max_length=255)),
                (
                    "visibility",
                    models.CharField(
                        choices=[
                            ("PRIVATE", "Private"),
                            ("ADMIN", "Admin only"),
                            ("PUBLIC", "Public"),
                        ],
                        default="PRIVATE",
                        max_length=20,
                    ),
                ),
                ("is_archived", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="created_files",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="deleted_files",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        help_text="Organization this file belongs to",
                        null=True,
                        on_delete=models.CASCADE,
                        related_name="files",
                        to="subscriptions.organization",
                    ),
                ),
            ],
            options={
                "db_table": "storage_files",
                "indexes": [
                    models.Index(
                        fields=["organization"],
                        name="storage_fi_organiz_0ef19b_idx",
                    ),
                    models.Index(
                        fields=["owner_type", "owner_id"],
                        name="storage_fi_owner_t_f8e7ff_idx",
                    ),
                    models.Index(
                        fields=["is_archived", "deleted_at"],
                        name="storage_fi_is_arch_d9c69c_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="FileActivity",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("uploaded", "Uploaded"),
                            ("downloaded", "Downloaded"),
                            ("archived", "Archived"),
                            ("restored", "Restored"),
                        ],
                        max_length=20,
                    ),
                ),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
                (
                    "file",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="activities",
                        to="storage.fileobject",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="file_activities",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "storage_file_activity",
                "indexes": [
                    models.Index(
                        fields=["file"], name="storage_fi_file_id_4b22a8_idx"
                    ),
                    models.Index(
                        fields=["user"], name="storage_fi_user_id_c8b42e_idx"
                    ),
                    models.Index(
                        fields=["action", "timestamp"],
                        name="storage_fi_action__343d1a_idx",
                    ),
                ],
            },
        ),
    ]




