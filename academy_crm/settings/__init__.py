# Import base settings
from .base import *

# Import environment-specific settings
import os

# Check if DJANGO_SETTINGS_MODULE is explicitly set (used by Render for prod/staging)
# If it's set to a specific module (e.g., academy_crm.settings.prod), Django will use that directly
# This file is only loaded if DJANGO_SETTINGS_MODULE is set to academy_crm.settings
django_settings_module = os.getenv('DJANGO_SETTINGS_MODULE', '')

# If DJANGO_SETTINGS_MODULE points to a specific settings file, don't auto-load here
# (Django will load it directly)
if django_settings_module and django_settings_module != 'academy_crm.settings':
    # Django will load the specific module, so we don't need to do anything here
    pass
else:
    # Fallback: Use DJANGO_ENV or auto-detect
    env = os.getenv('DJANGO_ENV', 'dev')
    
    # Auto-detect production environment on Render
    # Render sets RENDER environment variable
    if not env or env == 'dev':
        if os.getenv('RENDER') or os.getenv('RENDER_EXTERNAL_HOSTNAME'):
            env = 'prod'
    
    if env == 'prod':
        try:
            from .prod import *
        except ImportError:
            pass
    elif env == 'staging':
        try:
            from .staging import *
        except ImportError:
            pass
    else:
        try:
            from .dev import *
        except ImportError:
            pass
