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
                
                # Monkey-patch guardian's create_anonymous_user to do nothing during migrations
                # This is more reliable than disconnecting signals
                original_create_anonymous_user = management.create_anonymous_user
                
                def noop_create_anonymous_user(*args, **kwargs):
                    """No-op version that does nothing during migrations."""
                    # Additional safety: check if we're still in migrate context
                    if 'migrate' in sys.argv:
                        return
                    # If somehow we get here, try to handle gracefully
                    try:
                        # Only proceed if User model has all expected fields
                        from django.contrib.auth import get_user_model
                        User = get_user_model()
                        # Try a simple query to check if model is ready
                        User._meta.get_field('profile_picture')
                        # If we get here, model is ready, call original
                        return original_create_anonymous_user(*args, **kwargs)
                    except Exception:
                        # Model not ready, skip
                        return
                
                # Replace the function
                management.create_anonymous_user = noop_create_anonymous_user
                
                # Also try to disconnect the signal as backup
                disconnected = False
                
                # Approach 1: Disconnect with auth app as sender
                try:
                    auth_app = apps.get_app_config('auth')
                    post_migrate.disconnect(
                        original_create_anonymous_user,
                        sender=auth_app,
                        dispatch_uid='guardian.management.create_anonymous_user'
                    )
                    disconnected = True
                except (ValueError, TypeError):
                    pass
                
                # Approach 2: Disconnect without sender
                try:
                    post_migrate.disconnect(
                        original_create_anonymous_user,
                        dispatch_uid='guardian.management.create_anonymous_user'
                    )
                    disconnected = True
                except (ValueError, TypeError):
                    pass
                
                # Approach 3: Disconnect by function only
                try:
                    post_migrate.disconnect(original_create_anonymous_user)
                    disconnected = True
                except (ValueError, TypeError):
                    pass
                
                # Use print instead of logger since Django might not be fully configured
                print("⚠️  Guardian create_anonymous_user disabled for migrations")
            except ImportError:
                # Guardian not available, nothing to do
                pass
            except Exception:
                # Any other error - continue anyway
                pass

