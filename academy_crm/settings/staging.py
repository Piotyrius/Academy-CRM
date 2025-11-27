"""
Staging settings for Academy CRM.
Similar to production but with some relaxed settings for testing.
"""
from .base import *
from django.core.exceptions import ImproperlyConfigured

DEBUG = False

# SECRET_KEY must be explicitly set in the environment for staging and must
# not use the insecure default defined in base settings.
if not SECRET_KEY or SECRET_KEY == DEFAULT_INSECURE_SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY is not set or is using the insecure default. "
        "Set a strong SECRET_KEY environment variable for staging."
    )

# ALLOWED_HOSTS - filter out empty strings from comma-separated list
allowed_hosts_env = os.getenv('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]

# Add 'testserver' for Django test client (useful for debugging)
if 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')

# Debug: Log ALLOWED_HOSTS for troubleshooting
import logging
logger = logging.getLogger(__name__)
logger.info(f"ALLOWED_HOSTS from env: {allowed_hosts_env}")
logger.info(f"ALLOWED_HOSTS parsed: {ALLOWED_HOSTS}")

# Automatically allow Render.com subdomains
# Render sets RENDER_EXTERNAL_HOSTNAME environment variable
render_external_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if render_external_hostname:
    # Add the Render-provided hostname if not already in the list
    if render_external_hostname not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(render_external_hostname)
    
    # Also add the base onrender.com pattern for flexibility
    # Extract the service name and add common Render patterns
    if '.onrender.com' in render_external_hostname:
        # Add common Render hostname patterns
        base_domain = render_external_hostname.split('.onrender.com')[0]
        if base_domain:
            # Add variations that Render might use
            render_hosts = [
                render_external_hostname,
                f'{base_domain}.onrender.com',
            ]
            for host in render_hosts:
                if host not in ALLOWED_HOSTS:
                    ALLOWED_HOSTS.append(host)

# Also check if we're on Render infrastructure (even without RENDER_EXTERNAL_HOSTNAME)
# Render sets RENDER environment variable
if os.getenv('RENDER') == 'true' or os.getenv('RENDER'):
    # We're on Render - ensure we allow common Render patterns
    # The middleware will handle specific hostnames at runtime
    pass  # Middleware will add specific hosts

# Fallback: If still empty, set minimal defaults
if not ALLOWED_HOSTS:
    # Check if we're on Render infrastructure
    if os.getenv('RENDER') or os.getenv('RENDER_EXTERNAL_HOSTNAME'):
        # On Render but no ALLOWED_HOSTS set - middleware will handle it
        # But set a minimal default to avoid issues
        # The middleware will add the actual Render hostname at runtime
        ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Security settings
# Render uses a proxy that terminates SSL, so we need to trust the X-Forwarded-Proto header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Only redirect to HTTPS if we're sure we're behind a proxy (Render sets X-Forwarded-Proto)
# Disable automatic redirect to avoid loops - Render handles SSL termination
SECURE_SSL_REDIRECT = False  # Render handles SSL, so we don't need to redirect
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Email - use console backend for staging (or configure test SMTP)
# In staging, you might want to use a test email service or console backend
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@academy.edu.ge')

# Sentry - optional for staging (can use same DSN or separate staging DSN)
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='staging',  # Mark as staging environment
    )

# CORS - more permissive in staging for testing
# Filter out empty strings from comma-separated list
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if origin.strip()]

# Always allow localhost origins for local development (frontend developers)
# These are safe to include even in staging as they only work on localhost
LOCALHOST_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8080",
]

# Add localhost origins if not already present
for origin in LOCALHOST_ORIGINS:
    if origin not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(origin)

# In staging, be more permissive with CORS for testing
# You can restrict this later if needed
if not CORS_ALLOWED_ORIGINS:
    # Allow all origins for staging testing (you can restrict later)
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOW_CREDENTIALS = True

# Static files serving in staging
# Use WhiteNoise to serve static files efficiently
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# WhiteNoise configuration
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

# Logging - more verbose in staging for debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'academy_crm': {
            'handlers': ['console'],
            'level': 'DEBUG',  # More verbose in staging
            'propagate': False,
        },
    },
}

