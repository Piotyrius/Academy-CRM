from django.apps import AppConfig


class TimekeepingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'timekeeping'

    def ready(self):
        # Import signals on app ready
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Signals are optional in minimal bootstrap
            pass


