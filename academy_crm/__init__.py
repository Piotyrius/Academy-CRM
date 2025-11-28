"""
Academy CRM Django project package.

This module also wires in small compatibility shims needed for some
third-party packages when running on modern Django versions.
"""

# Ensure compatibility helpers (e.g. force_text alias) are applied as early
# as possible, before apps and models are imported.
from . import compat  # noqa: F401

# Import celery app (optional - only if Celery is installed)
try:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
except ImportError:
    # Celery not installed or not configured
    celery_app = None
    __all__ = ()
