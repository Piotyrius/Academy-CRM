# Import base settings
from .base import *

# Import environment-specific settings
import os

env = os.getenv('DJANGO_ENV', 'dev')

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
