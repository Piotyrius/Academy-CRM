#!/usr/bin/env python
"""
Wrapper script to run migrations with guardian signal disabled.
This ensures guardian doesn't query User model during migrations.
"""
import os
import sys
import django

# Set environment variable before Django loads
os.environ['DISABLE_GUARDIAN_SIGNAL'] = '1'

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academy_crm.settings')
django.setup()

# Disconnect guardian signal right before running migrate
from django.db.models.signals import post_migrate
from django.apps import apps

def disconnect_guardian():
    """Disconnect guardian signal using multiple approaches."""
    try:
        from guardian import management
        
        # Try multiple approaches to disconnect
        auth_app = apps.get_app_config('auth')
        disconnected = False
        
        # Approach 1: With auth app as sender
        try:
            post_migrate.disconnect(
                management.create_anonymous_user,
                sender=auth_app,
                dispatch_uid='guardian.management.create_anonymous_user'
            )
            disconnected = True
        except (ValueError, TypeError):
            pass
        
        # Approach 2: Without sender
        try:
            post_migrate.disconnect(
                management.create_anonymous_user,
                dispatch_uid='guardian.management.create_anonymous_user'
            )
            disconnected = True
        except (ValueError, TypeError):
            pass
        
        # Approach 3: By function only
        try:
            post_migrate.disconnect(management.create_anonymous_user)
            disconnected = True
        except (ValueError, TypeError):
            pass
        
        if disconnected:
            print("⚠️  Guardian signal disconnected before migrations")
    except ImportError:
        pass
    except Exception:
        pass

# Disconnect before migrations
disconnect_guardian()

# Also connect a signal handler that runs BEFORE guardian's to prevent it
def prevent_guardian_query(sender, **kwargs):
    """Prevent guardian from querying by disconnecting it again."""
    disconnect_guardian()

# Connect our handler to run before guardian's (lower priority number = runs first)
try:
    from django.apps import apps as django_apps
    auth_app = django_apps.get_app_config('auth')
    post_migrate.connect(
        prevent_guardian_query,
        sender=auth_app,
        dispatch_uid='prevent_guardian_query',
        weak=False
    )
except Exception:
    pass

# Now run the migrate command
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    execute_from_command_line(['manage.py', 'migrate'] + sys.argv[1:])

