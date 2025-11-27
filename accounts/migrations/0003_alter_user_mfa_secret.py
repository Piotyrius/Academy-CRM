# Generated migration to convert mfa_secret from CharField to EncryptedTextField
# This migration clears existing mfa_secret data to prevent encoding errors
# Users will need to re-enable MFA after this migration

from django.db import migrations, models
import fernet_fields.fields


def clear_mfa_secrets(apps, schema_editor):
    """Clear existing mfa_secret values to prevent encoding errors."""
    User = apps.get_model('accounts', 'User')
    # Clear all mfa_secret values and disable MFA
    User.objects.filter(mfa_secret__isnull=False).update(
        mfa_secret=None,
        mfa_enabled=False
    )


def reverse_clear_mfa_secrets(apps, schema_editor):
    """Reverse operation - nothing to do as we can't restore the data."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_organization_user_users_organiz_ca9165_idx'),
    ]

    operations = [
        # Step 1: Clear existing data to prevent encoding errors
        migrations.RunPython(
            clear_mfa_secrets,
            reverse_clear_mfa_secrets,
        ),
        # Step 2: Convert field from CharField to EncryptedTextField
        migrations.AlterField(
            model_name='user',
            name='mfa_secret',
            field=fernet_fields.fields.EncryptedTextField(
                blank=True,
                help_text='MFA secret key (encrypted)',
                null=True
            ),
        ),
    ]

