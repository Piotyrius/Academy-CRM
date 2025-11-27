# Generated migration to convert mfa_secret from CharField to EncryptedTextField
# This migration clears existing mfa_secret data to prevent encoding errors
# Users will need to re-enable MFA after this migration

from django.db import migrations, models
import fernet_fields.fields


def clear_mfa_secrets(apps, schema_editor):
    """Clear existing mfa_secret values to prevent encoding errors."""
    User = apps.get_model('accounts', 'User')
    # Clear all mfa_secret values and disable MFA
    # Set to None (NULL) - the field now allows null=True
    User.objects.filter(mfa_secret__isnull=False).exclude(mfa_secret='').update(
        mfa_secret=None,
        mfa_enabled=False
    )


def ensure_null_values_after_conversion(apps, schema_editor):
    """
    After converting to EncryptedTextField, ensure NULL values stay NULL.
    This prevents fernet_fields from trying to decrypt NULL values.
    """
    # This function runs after the field conversion
    # NULL values are already NULL, so nothing to do
    # But we ensure the field properly handles NULL
    pass


def reverse_clear_mfa_secrets(apps, schema_editor):
    """Reverse operation - nothing to do as we can't restore the data."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_organization_user_users_organiz_ca9165_idx'),
    ]

    operations = [
        # Step 1: First alter CharField to allow null=True (if it doesn't already)
        # This ensures we can set values to None if needed
        migrations.AlterField(
            model_name='user',
            name='mfa_secret',
            field=models.CharField(
                blank=True,
                help_text='MFA secret key',
                max_length=32,
                null=True
            ),
        ),
        # Step 2: Clear existing data to prevent encoding errors
        migrations.RunPython(
            clear_mfa_secrets,
            reverse_clear_mfa_secrets,
        ),
        # Step 3: Convert field from CharField to EncryptedTextField
        migrations.AlterField(
            model_name='user',
            name='mfa_secret',
            field=fernet_fields.fields.EncryptedTextField(
                blank=True,
                help_text='MFA secret key (encrypted)',
                null=True
            ),
        ),
        # Step 4: Ensure NULL values are properly handled
        # This is a no-op but ensures the migration completes properly
        migrations.RunPython(
            ensure_null_values_after_conversion,
            reverse_clear_mfa_secrets,
        ),
    ]

