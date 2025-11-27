"""
Accounts app configuration for Academy CRM.
"""
import sys
from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccountsConfig(AppConfig):
    """Configuration for accounts app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Accounts'

    def ready(self):
        """
        Disconnect guardian's post_migrate signal during migrations.
        
        This prevents fernet_fields encoding errors when guardian queries User model
        before the mfa_secret field is converted from CharField to EncryptedTextField.
        
        The signal is disconnected only during migrations to avoid interfering with
        normal operation where guardian's anonymous user creation is needed.
        """
        # Check if we're running migrations
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            try:
                from guardian import management
                
                # Disconnect guardian's post_migrate signal
                try:
                    post_migrate.disconnect(
                        management.create_anonymous_user,
                        dispatch_uid='guardian.management.create_anonymous_user'
                    )
                    # Use print instead of logger since Django might not be fully configured
                    print("⚠️  Guardian post_migrate signal disconnected for migrations")
                except (ValueError, TypeError):
                    # Signal not connected yet, that's fine
                    # It might not be connected if guardian hasn't loaded yet
                    pass
            except ImportError:
                # Guardian not available, nothing to do
                pass

