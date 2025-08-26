"""
Django settings for Docker deployment.
This file overrides the main settings.py for containerized environments.
"""

from .settings import *
import os

# Override DEBUG for production
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Database configuration for PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'face_ai_db'),
        'USER': os.environ.get('POSTGRES_USER', 'face_ai_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'face_ai_password'),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# Cache configuration for Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://redis:6379/0'),
    }
}

# Session configuration for Redis - SECURE SETTINGS
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 3600  # 1 hour in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Session expires when browser closes
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_MAX_AGE = 3600  # 1 hour maximum
SESSION_TIMEOUT_WARNING = 300  # Show warning 5 minutes before expiry
SESSION_TIMEOUT_REDIRECT = 60  # Redirect to login 1 minute before expiry
SESSION_ABSOLUTE_TIMEOUT = 3600  # Absolute maximum 1 hour

# Celery configuration
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Milvus configuration - using external service
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
    'AUTO_CREATE_COLLECTION': os.environ.get('MILVUS_AUTO_CREATE', 'True').lower() == 'true',
    'AUTO_LOAD_COLLECTION': os.environ.get('MILVUS_AUTO_LOAD', 'True').lower() == 'true',
}

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = False  # Set to True if using HTTPS
    CSRF_COOKIE_SECURE = False  # Set to True if using HTTPS
    SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS

# CSRF settings
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:80',
    'http://127.0.0.1:80',
    'http://localhost',
    'http://127.0.0.1',
]

# Allowed hosts for Docker
ALLOWED_HOSTS = ['*']

# Static files configuration for Docker
STATIC_ROOT = '/app/staticfiles'
MEDIA_ROOT = '/app/media'

# Logging configuration for Docker
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
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/app/logs/django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'backendapp': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'face_ai': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Health check endpoint
HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # percentage
    'MEMORY_MIN': 100,     # MB
}
