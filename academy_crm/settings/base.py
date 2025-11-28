"""
Base settings for Academy CRM project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# Default is only for local development and tests; production must override.
DEFAULT_INSECURE_SECRET_KEY = 'django-insecure-0w$j%9y@!300$#0xw58-ohk6rqnwicp#6q+ys8x9vv#js^xqj$'
SECRET_KEY = os.getenv('SECRET_KEY', DEFAULT_INSECURE_SECRET_KEY)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'guardian',
    'django_filters',
    'simple_history',
    'import_export',
    'drf_spectacular',
    'health_check',
    'health_check.db',
    # 'health_check.cache',  # Will be conditionally added if Redis is enabled
    # 'health_check.storage',  # Disabled - only enable if using cloud storage
    'axes',
    
    # Local apps
    'subscriptions',  # Multi-tenant and subscription management (must be before other apps)
    'accounts.apps.AccountsConfig',  # Use explicit AppConfig to enable ready() method
    'academy_crm',  # Project app (needed for management commands)
    'catalog',
    'admissions',
    'attendance',
    'assessment',
    'certificates',
    'documents',
    'notifications',
    'reporting',
    'ops',
    'timekeeping',
    'gallery',
    'payments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files in production
    'academy_crm.middleware.RenderHostMiddleware',  # Allow Render subdomains
    'subscriptions.middleware.TenantMiddleware',  # Multi-tenant organization identification (early in chain)
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'academy_crm.middleware.RenderCommonMiddleware',  # Custom CommonMiddleware that allows Render hosts
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'academy_crm.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'academy_crm.wsgi.application'

# Database
# PostgreSQL is required - UUID primary keys require PostgreSQL
# Supports both DATABASE_URL (Render standard) and individual DB_* variables

import logging
logger = logging.getLogger(__name__)

# Primary method: Use DATABASE_URL if provided (Render standard)
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Parse DATABASE_URL: postgresql://user:password@host:port/database
    try:
        from urllib.parse import urlparse, unquote
        parsed = urlparse(DATABASE_URL)
        
        # Extract components
        db_name = parsed.path.lstrip('/') if parsed.path else 'academy_crm'
        db_user = unquote(parsed.username) if parsed.username else 'postgres'
        db_password = unquote(parsed.password) if parsed.password else ''
        db_host = parsed.hostname if parsed.hostname else 'localhost'
        db_port = parsed.port if parsed.port else '5432'
        
        # Allow DB_NAME to override database name from DATABASE_URL
        # This is useful when Render's DATABASE_URL points to "Default" but you want "academy_crm"
        explicit_db_name = os.getenv('DB_NAME')
        if explicit_db_name:
            original_db_name = db_name
            db_name = explicit_db_name
            logger.info(f"Using DATABASE_URL but overriding database name: '{original_db_name}' -> '{db_name}' (from DB_NAME)")
        else:
            logger.info(f"Using DATABASE_URL (database: {db_name}, host: {db_host})")
        
        # Also allow other DB_* variables to override if explicitly set
        # This allows fine-tuning connection even when DATABASE_URL is provided by Render
        if os.getenv('DB_USER'):
            db_user = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD'):
            db_password = os.getenv('DB_PASSWORD')
        if os.getenv('DB_HOST'):
            # If DB_HOST is set, use it (extract hostname if it's a URL)
            explicit_db_host = os.getenv('DB_HOST')
            if explicit_db_host.startswith(('postgresql://', 'postgres://')):
                # Parse URL to get just hostname
                from urllib.parse import urlparse
                parsed_host = urlparse(explicit_db_host)
                db_host = parsed_host.hostname or parsed_host.netloc.split('@')[-1].split(':')[0]
            else:
                db_host = explicit_db_host
        if os.getenv('DB_PORT'):
            db_port = os.getenv('DB_PORT')
        
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': db_name,
                'USER': db_user,
                'PASSWORD': db_password,
                'HOST': db_host,
                'PORT': db_port,
                'OPTIONS': {
                    'connect_timeout': 10,
                },
            }
        }
    except Exception as e:
        logger.error(f"Failed to parse DATABASE_URL: {e}")
        # Fall through to individual variables
        DATABASE_URL = None

# Fallback: Use individual DB_* environment variables
if not DATABASE_URL:
    # Helper function to extract hostname from DB_HOST if it's a full URL
    def get_db_host():
        """Extract hostname from DB_HOST, handling both URL and hostname formats."""
        db_host = os.getenv('DB_HOST', 'localhost')
        
        # Safety check: if DB_HOST looks like a password (starts with alphanumeric and has @), it's wrong
        if db_host and '@' in db_host and not db_host.startswith(('postgresql://', 'postgres://', 'http://', 'https://')):
            # This looks like password@host format - extract hostname
            if '@' in db_host:
                host_part = db_host.split('@')[-1]
                # Remove database name if present (host/db)
                hostname = host_part.split('/')[0]
                # Remove port if present
                hostname = hostname.split(':')[0]
                return hostname
        
        # If it's a full PostgreSQL URL, extract just the hostname
        if db_host.startswith('postgresql://') or db_host.startswith('postgres://'):
            # Parse the URL: postgresql://user:pass@host:port/db
            try:
                from urllib.parse import urlparse
                parsed = urlparse(db_host)
                # Extract hostname (remove port if present)
                hostname = parsed.hostname or parsed.netloc.split('@')[-1].split(':')[0]
                return hostname
            except Exception:
                # If parsing fails, try to extract manually
                if '@' in db_host:
                    # Extract hostname from postgresql://user:pass@host/db
                    host_part = db_host.split('@')[-1].split('/')[0]
                    # Remove port if present
                    hostname = host_part.split(':')[0]
                    return hostname
        
        # If it's already just a hostname, return as-is
        return db_host

    # Get database host (handles both URL and hostname formats)
    db_host_raw = os.getenv('DB_HOST', 'localhost')
    db_host = get_db_host()

    # Log database configuration (without password) for debugging
    logger.warning(f"DB_HOST (raw): {db_host_raw[:50]}..." if len(db_host_raw) > 50 else f"DB_HOST (raw): {db_host_raw}")
    logger.info(f"Database HOST (parsed): {db_host}")
    logger.info(f"Database NAME: {os.getenv('DB_NAME', 'academy_crm')}")
    logger.info(f"Database USER: {os.getenv('DB_USER', 'postgres')}")
    logger.info(f"Database PORT: {os.getenv('DB_PORT', '5432')}")

    # Warn if DB_HOST looks wrong
    if '@' in db_host_raw and not db_host_raw.startswith(('postgresql://', 'postgres://')):
        logger.error(f"⚠️ DB_HOST appears to have password mixed in! Raw value: {db_host_raw[:50]}...")
        logger.error(f"✅ Parsed hostname: {db_host}")
        logger.error("⚠️ Please fix DB_HOST in Render environment variables to be just the hostname!")

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'academy_crm'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
            'HOST': db_host,
            'PORT': os.getenv('DB_PORT', '5432'),
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ka'  # Georgian
TIME_ZONE = 'Asia/Tbilisi'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django Guardian and Axes
AUTHENTICATION_BACKENDS = (
    'axes.backends.AxesStandaloneBackend',  # Axes login lockout (must be first)
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

# Note: Guardian signal disconnection is handled in migrate_safe_guardian management command
# We can't do it here in settings because Django apps aren't loaded yet (circular dependency)

# REST Framework
REST_FRAMEWORK = {
    # Only JWT for API - Session auth is only for Django admin
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # SessionAuthentication removed - only needed for Django admin, not API
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # Ensure JSON renderer is always available for proper content negotiation
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        # Enable form and file uploads (e.g. gallery works with images)
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login_anon': '10/minute',
        'login_user': '30/minute',
        'password_reset_anon': '5/minute',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Simple JWT
from datetime import timedelta
SIMPLE_JWT = {
    # Short-lived access tokens; refresh tokens are used to obtain new ones.
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=20),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    # Only accept explicit Bearer tokens in the Authorization header.
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8080",
]

# Redis Cache (fallback to dummy cache if Redis is not available)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
USE_REDIS = os.getenv('USE_REDIS', 'False').lower() == 'true'

if USE_REDIS:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
    # Enable cache health check only if Redis is configured
    if 'health_check.cache' not in INSTALLED_APPS:
        INSTALLED_APPS.append('health_check.cache')
else:
    # Use dummy cache for development when Redis is not available
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
    # Remove cache health check if using dummy cache (it will fail)
    if 'health_check.cache' in INSTALLED_APPS:
        INSTALLED_APPS.remove('health_check.cache')

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Django Axes (Login throttling)
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
# Use database lockout (requires database connection)
try:
    from axes.lockout import database_lockout
    AXES_LOCKOUT_CALLABLE = database_lockout
except ImportError:
    # Fallback if axes lockout not available
    AXES_LOCKOUT_CALLABLE = None

# Sentry (will be configured in prod)
SENTRY_DSN = os.getenv('SENTRY_DSN', '')

# DRF Spectacular (OpenAPI)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Academy CRM API',
    'DESCRIPTION': 'REST API for Academy CRM Backend',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': True,  # Include schema in response
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    # By default, require authentication for serving schema; CustomSpectacularAPIView
    # further relaxes this in DEBUG for local development.
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAuthenticated'],
    'SERVE_AUTHENTICATION': 'rest_framework_simplejwt.authentication.JWTAuthentication',
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    # Make schema generation work without database
    'DISABLE_ERRORS_AND_WARNINGS': False,
    'PREPROCESSING_HOOKS': [],
    'POSTPROCESSING_HOOKS': [],
    # Cache schema generation
    'SCHEMA_PATH_PREFIX_TRIM': False,  # Keep full paths with /api/v1/ prefix in schema
    'SCHEMA_COERCE_PATH_PK': True,
    # Servers configuration for Swagger UI (optional - paths already include full prefix)
    'SERVERS': [
        {'url': 'https://academy-crm.onrender.com', 'description': 'Production server'},
    ],
    'SCHEMA_COERCE_METHOD_NAMES': {
        'retrieve': 'read',
        'list': 'list',
        'create': 'create',
        'update': 'update',
        'partial_update': 'partial_update',
        'destroy': 'delete',
    },
    # Make Swagger UI accessible without authentication
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'displayOperationId': True,
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
        'docExpansion': 'list',
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
        'tryItOutEnabled': True,
        'persistAuthorization': True,
    },
    # Security settings for Swagger - Only JWT Bearer token
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'JWT token obtained from /api/v1/auth/login/ endpoint'
            }
        }
    },
    'SECURITY': [{'BearerAuth': []}],  # Default security for all endpoints - only JWT
    # Tags for better organization
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication endpoints'},
        {'name': 'Users', 'description': 'User management'},
        {'name': 'Catalog', 'description': 'Programs and courses'},
        {'name': 'Admissions', 'description': 'Student admissions'},
        {'name': 'Attendance', 'description': 'Attendance tracking'},
        {'name': 'Assessment', 'description': 'Assessments and grades'},
        {'name': 'Certificates', 'description': 'Certificate management'},
        {'name': 'Documents', 'description': 'Document management'},
        {'name': 'Timekeeping', 'description': 'Work logs and timesheets'},
        {'name': 'Gallery', 'description': 'Gallery management'},
        {'name': 'Reporting', 'description': 'Reports and exports'},
    ],
}

# Logging
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
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Security settings (override in prod)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Frontend URL for password reset links
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:8080')
