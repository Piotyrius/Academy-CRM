from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("storage", "0001_initial"),
        ("documents", "0002_document_organization_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="file",
            field=models.FileField(blank=True, upload_to="documents/"),
        ),
        migrations.AddField(
            model_name="document",
            name="file_object",
            field=models.ForeignKey(
                blank=True,
                help_text="Backed file object in Google Drive or other storage",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="documents",
                to="storage.fileobject",
            ),
        ),
    ]














