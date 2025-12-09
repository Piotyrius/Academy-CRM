from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("storage", "0001_initial"),
        ("gallery", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="work",
            name="media",
            field=models.FileField(blank=True, upload_to="gallery/"),
        ),
        migrations.AddField(
            model_name="work",
            name="file_object",
            field=models.ForeignKey(
                blank=True,
                help_text="Backed file object in Google Drive or other storage",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="gallery_works",
                to="storage.fileobject",
            ),
        ),
    ]








