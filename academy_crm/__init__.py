# Import celery app (optional - only if Celery is installed)
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not installed or not configured
    celery_app = None
    __all__ = ()
