"""
Development settings for Academy CRM.
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'testserver']  # testserver for test client

# Email backend (console for dev)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Debug toolbar (if installed)
if DEBUG:
    try:
        import debug_toolbar
        INSTALLED_APPS += ['debug_toolbar']
        MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
        INTERNAL_IPS = ['127.0.0.1']
    except ImportError:
        pass

# Enable query profiling in dev
ENABLE_QUERY_PROFILING = True
# Add query profiling middleware after TenantMiddleware
if 'academy_crm.middleware.QueryProfilingMiddleware' not in MIDDLEWARE:
    tenant_index = MIDDLEWARE.index('subscriptions.middleware.TenantMiddleware')
    MIDDLEWARE.insert(tenant_index + 1, 'academy_crm.middleware.QueryProfilingMiddleware')

# CORS - allow all in dev
CORS_ALLOW_ALL_ORIGINS = True

# Disable some security features in dev
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
