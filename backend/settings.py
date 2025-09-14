"""
Production Django settings for backend project.
This file contains production-grade security configurations.
"""

import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY: Generate a strong secret key if not provided
def get_secret_key():
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        raise ImproperlyConfigured(
            'SECRET_KEY environment variable is required for production. '
            'Please set a strong random secret key.'
        )
    if len(secret_key) < 50:
        raise ImproperlyConfigured(
            'SECRET_KEY must be at least 50 characters long for production security.'
        )
    return secret_key

SECRET_KEY = get_secret_key()

# SECURITY: Production mode - DEBUG must be False
DEBUG = False

# SECURITY: Restrict allowed hosts - never use '*' in production
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS environment variable is required for production security.'
    )

# Application definition
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Third-party security apps (optional - uncomment when packages are installed)
    "django_ratelimit",  # Rate limiting
    "csp",  # Content Security Policy
    # "django_helmet",  # Security headers - package not available

    # Project apps
    "backendapp",
    "notifications",
    "video_player",
    "source_management",
    "face_ai",
    "reports",
]

MIDDLEWARE = [
    # Security middleware (order is important)
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Static files

    # Django security middleware
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",  # Content Security Policy
    "django.middleware.csrf.CsrfViewMiddleware",

    # Core middleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",

    # Custom security middleware
    "backendapp.middleware.SessionMonitoringMiddleware",
    "backendapp.middleware.SessionTimeoutMiddleware",
    "backendapp.middleware.SecurityMiddleware",

    # Rate limiting
    "django_ratelimit.middleware.RatelimitMiddleware",
]

ROOT_URLCONF = "backend.urls"

# SECURITY: Secure template configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'backendapp' / 'templates'],
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

WSGI_APPLICATION = "backend.wsgi.application"
ASGI_APPLICATION = "backend.asgi.application"

# SECURITY: Production database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'face_ai_prod'),
        'USER': os.environ.get('POSTGRES_USER', 'face_ai_prod_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',  # Enforce SSL
            'sslcert': os.environ.get('SSL_CERT_PATH'),
            'sslkey': os.environ.get('SSL_KEY_PATH'),
            'sslrootcert': os.environ.get('SSL_ROOT_CERT_PATH'),
        },
        'CONN_MAX_AGE': 60,  # Connection pooling
        'ATOMIC_REQUESTS': True,  # Transaction wrapping
    }
}

# SECURITY: Redis cache for production
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_CACHE_URL', 'redis://127.0.0.1:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 20,
                'decode_responses': True,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        }
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_SESSION_URL', 'redis://127.0.0.1:6379/3'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# SECURITY: Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
SESSION_COOKIE_AGE = 1800  # 30 minutes for security
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # Strict same-site policy
SESSION_SAVE_EVERY_REQUEST = False

# SECURITY: CSRF protection
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
CSRF_USE_SESSIONS = False  # Use cookies for CSRF tokens

# SECURITY: Authentication settings
AUTH_USER_MODEL = 'backendapp.CustomUser'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# SECURITY: Password validation (enhanced for production)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validators.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'max_similarity': 0.7,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validators.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 16,  # Increased for production
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validators.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validators.NumericPasswordValidator',
    },
    {
        'NAME': 'backendapp.validators.CustomPasswordValidator',  # Custom validator
    },
]

# SECURITY: Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# SECURITY: Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# SECURITY: Media files (with restrictions)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# SECURITY: File upload restrictions
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_TEMP_DIR = BASE_DIR / 'temp'
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# SECURITY: HTTPS and SSL configuration
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = []  # No exemptions for SSL redirect
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# SECURITY: HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# SECURITY: Browser security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# SECURITY: Content Security Policy (CSP)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "https://cdn.jsdelivr.net", "https://code.jquery.com")
CSP_STYLE_SRC = ("'self'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_SRC = ("'none'",)
CSP_OBJECT_SRC = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)

# SECURITY: Rate limiting configuration
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_KEY_PREFIX = 'rl'
RATELIMIT_VIEW = 'backendapp.views.ratelimit_view'

# Custom rate limit rates
LOGIN_RATELIMIT = os.environ.get('LOGIN_RATELIMIT', '3/m')
API_RATELIMIT = os.environ.get('API_RATELIMIT', '100/h')
SEARCH_RATELIMIT = os.environ.get('SEARCH_RATELIMIT', '30/m')

# SECURITY: Logging configuration (production-grade)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        },
        'security': {
            'format': '[SECURITY] {levelname} {asctime} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': 'INFO',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
            'level': 'WARNING',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 10485760,
            'backupCount': 10,
            'formatter': 'security',
            'level': 'WARNING',
        },
        'json_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.json',
            'maxBytes': 10485760,
            'backupCount': 10,
            'formatter': 'json',
            'level': 'INFO',
        },
    },
    'root': {
        'handlers': ['console', 'file', 'json_file'],
        'level': os.environ.get('LOG_LEVEL', 'WARNING'),
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'backendapp': {
            'handlers': ['console', 'file', 'json_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'face_ai': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# SECURITY: Admin configuration
ADMIN_ENABLED = os.environ.get('ADMIN_ENABLED', 'true').lower() == 'true'
# Admin is already included in INSTALLED_APPS above

# SECURITY: Django REST Framework (if used)
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# SECURITY: Custom security settings
SESSION_MONITORING_ENABLED = True
SESSION_ACTIVITY_LOGGING = True
SESSION_EXPIRY_LOGGING = True
SESSION_TIMEOUT_WARNING = 300  # 5 minutes
SESSION_TIMEOUT_REDIRECT = 60  # 1 minute
SESSION_ABSOLUTE_TIMEOUT = 1800  # 30 minutes

# SECURITY: Email configuration (encrypted connection required)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@your-domain.com')

# SECURITY: Admin and manager notifications
ADMINS = [('Admin', os.environ.get('ADMIN_EMAIL', 'admin@your-domain.com'))]
MANAGERS = [('Manager', os.environ.get('MANAGER_EMAIL', 'manager@your-domain.com'))]

# SECURITY: Custom security middleware settings
SECURITY_MIDDLEWARE_ENABLED = True
BLOCKED_IPS = os.environ.get('BLOCKED_IPS', '').split(',')
ALLOWED_IPS = os.environ.get('ALLOWED_IPS', '').split(',')
SQL_INJECTION_PROTECTION = True
XSS_PROTECTION = True
CSRF_PROTECTION_ENHANCED = True

# SECURITY: Performance and resource limits
MAX_REQUEST_SIZE = 10485760  # 10MB
MAX_FILE_SIZE = 536870912  # 512MB
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 3600  # 1 hour

# SECURITY: Monitoring and alerting
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )

# SECURITY: Prometheus metrics (if enabled)
PROMETHEUS_METRICS_ENABLED = os.environ.get('ENABLE_PROMETHEUS_METRICS', 'false').lower() == 'true'
if PROMETHEUS_METRICS_ENABLED:
    INSTALLED_APPS.append('django_prometheus')
    MIDDLEWARE.insert(0, 'django_prometheus.middleware.PrometheusBeforeMiddleware')
    MIDDLEWARE.append('django_prometheus.middleware.PrometheusAfterMiddleware')

# Application-specific settings (with security considerations)
MILVUS_CONFIG = {
    'HOST': os.environ.get('MILVUS_HOST', 'localhost'),
    'PORT': int(os.environ.get('MILVUS_PORT', '19530')),
    'COLLECTION_NAME': os.environ.get('MILVUS_COLLECTION_NAME', 'watchlist'),
    'COLLECTION_PREFIX': os.environ.get('MILVUS_COLLECTION_PREFIX', 'surveillance_'),
    'DIMENSION': int(os.environ.get('MILVUS_DIMENSION', '512')),
    'METRIC_TYPE': os.environ.get('MILVUS_METRIC_TYPE', 'COSINE'),
    'INDEX_TYPE': os.environ.get('MILVUS_INDEX_TYPE', 'IVF_FLAT'),
    'INDEX_PARAMS': {
        'nlist': int(os.environ.get('MILVUS_INDEX_NLIST', '1024'))
    },
    'SEARCH_PARAMS': {
        'nprobe': int(os.environ.get('MILVUS_SEARCH_NPROBE', '10'))
    },
    'CONNECTION_ALIAS': os.environ.get('MILVUS_CONNECTION_ALIAS', 'default'),
    'AUTO_CREATE_COLLECTION': os.environ.get('MILVUS_AUTO_CREATE_COLLECTION', 'True').lower() == 'true',
    'AUTO_LOAD_COLLECTION': os.environ.get('MILVUS_AUTO_LOAD_COLLECTION', 'True').lower() == 'true',
}

# Security: Face detection service (HTTPS recommended for production)
FACE_DETECTION_SERVICE_URL = os.environ.get('FACE_DETECTION_SERVICE_URL')
if FACE_DETECTION_SERVICE_URL and not FACE_DETECTION_SERVICE_URL.startswith(('https://', 'http://')):
    raise ImproperlyConfigured('FACE_DETECTION_SERVICE_URL must be a valid URL')

# Security: Data ingestion service (with API key)
DATA_INGESTION_SERVICE = {
    'BASE_URL': os.environ.get('DATA_INGESTION_SERVICE_URL'),
    'NOTIFY_ENDPOINT': '/api/sources',
    'HEALTH_ENDPOINT': '/health',
    'STATUS_ENDPOINT': '/api/sources/{source_id}/status',
    'API_KEY': os.environ.get('DATA_INGESTION_API_KEY'),
    'TIMEOUT': int(os.environ.get('DATA_INGESTION_TIMEOUT', 60)),
}

# Security: File upload constraints (stricter for production)
MAX_UPLOAD_SIZE = int(os.environ.get('MAX_UPLOAD_SIZE', 104857600))  # 100MB
MAX_VIDEO_FILE_SIZE = int(os.environ.get('MAX_VIDEO_FILE_SIZE', 536870912))  # 512MB
CHUNKED_UPLOAD_THRESHOLD = int(os.environ.get('CHUNKED_UPLOAD_THRESHOLD', 104857600))

# Security: External service configuration (with authentication)
STREAM_PROCESSSING_SERVICE = {
    'ENABLED': os.environ.get('DOWNSTREAM_SERVICE_ENABLED', 'false').lower() == 'true',
    'URL': os.environ.get('DOWNSTREAM_SERVICE_URL'),
    'API_TOKEN': os.environ.get('DOWNSTREAM_SERVICE_TOKEN'),
    'TIMEOUT': int(os.environ.get('DOWNSTREAM_SERVICE_TIMEOUT', 30)),
    'RETRY_ATTEMPTS': int(os.environ.get('DOWNSTREAM_SERVICE_RETRY_ATTEMPTS', 5)),
    'BATCH_SIZE': int(os.environ.get('DOWNSTREAM_SERVICE_BATCH_SIZE', 50)),
    'ENABLE_ANALYTICS': os.environ.get('DOWNSTREAM_SERVICE_ENABLE_ANALYTICS', 'true').lower() == 'true',
    'ENABLE_EVENTS': os.environ.get('DOWNSTREAM_SERVICE_ENABLE_EVENTS', 'true').lower() == 'true',
}

# Security: Base URL (HTTPS recommended for production)
BASE_URL = os.environ.get('BASE_URL')
if BASE_URL and not BASE_URL.startswith(('https://', 'http://')):
    raise ImproperlyConfigured('BASE_URL must be a valid URL')

# Security: Additional production settings
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
