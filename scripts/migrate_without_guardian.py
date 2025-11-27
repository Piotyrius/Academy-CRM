"""
Run migrations with guardian signal disabled.
This prevents fernet_fields encoding errors when guardian queries User model.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academy_crm.settings')
django.setup()

from django.core.management import call_command
from django.db.models.signals import post_migrate

# Disconnect guardian's signal before migrations
try:
    from guardian import management
    
    # Disconnect the signal
    try:
        post_migrate.disconnect(
            management.create_anonymous_user,
            dispatch_uid='guardian.management.create_anonymous_user'
        )
        print("✅ Guardian post_migrate signal disconnected")
    except (ValueError, TypeError):
        # Signal not connected yet, that's fine
        print("⚠️  Guardian signal not connected (OK)")
except ImportError:
    # Guardian not available
    print("⚠️  Guardian not available")

# Get app_label from command line args
app_label = sys.argv[1] if len(sys.argv) > 1 else None
noinput = '--noinput' in sys.argv

# Run migrations
try:
    if app_label:
        call_command('migrate', app_label, verbosity=1, noinput=noinput)
    else:
        call_command('migrate', verbosity=1, noinput=noinput)
    print("✅ Migrations completed successfully")
except Exception as e:
    print(f"❌ Migrations failed: {e}")
    sys.exit(1)

