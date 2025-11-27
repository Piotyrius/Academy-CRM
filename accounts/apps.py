"""
Accounts app configuration for Academy CRM.
"""
import os
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
        # Check if we should disable guardian signal (via environment variable or migrate command)
        disable_guardian = (
            os.getenv('DISABLE_GUARDIAN_SIGNAL', '').lower() == '1' or
            'migrate' in sys.argv or 
            'makemigrations' in sys.argv
        )
        
        if disable_guardian:
            try:
                from guardian import management
                from django.apps import apps
                
                # Disconnect guardian's post_migrate signal - try multiple approaches
                disconnected = False
                
                # Approach 1: Disconnect with auth app as sender (guardian's typical setup)
                try:
                    auth_app = apps.get_app_config('auth')
                    post_migrate.disconnect(
                        management.create_anonymous_user,
                        sender=auth_app,
                        dispatch_uid='guardian.management.create_anonymous_user'
                    )
                    disconnected = True
                except (ValueError, TypeError):
                    pass
                
                # Approach 2: Disconnect without sender
                try:
                    post_migrate.disconnect(
                        management.create_anonymous_user,
                        dispatch_uid='guardian.management.create_anonymous_user'
                    )
                    disconnected = True
                except (ValueError, TypeError):
                    pass
                
                # Approach 3: Disconnect by function only
                try:
                    post_migrate.disconnect(management.create_anonymous_user)
                    disconnected = True
                except (ValueError, TypeError):
                    pass
                
                if disconnected:
                    # Use print instead of logger since Django might not be fully configured
                    print("⚠️  Guardian post_migrate signal disconnected for migrations")
            except ImportError:
                # Guardian not available, nothing to do
                pass
            except Exception:
                # Any other error - continue anyway
                pass

