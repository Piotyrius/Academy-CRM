# Import base settings
from .base import *

# Import environment-specific settings
import os

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
else:
    try:
        from .dev import *
    except ImportError:
        pass
