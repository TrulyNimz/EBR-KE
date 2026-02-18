"""
Testing settings for EBR Platform.

Uses SQLite in-memory for fast test runs.
Multi-tenant middleware is still active; tests use TenantTestCase
or create tenants manually via conftest fixtures.
"""
from .base import *

DEBUG = False
SECRET_KEY = 'test-secret-key-not-for-production'

ALLOWED_HOSTS = ['*']

# Fast password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# SQLite in-memory for speed
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': ':memory:',
        # SQLite doesn't support schemas, so we use PostgreSQL in CI.
        # For local test runs without PostgreSQL, override with:
        # ENGINE: 'django.db.backends.sqlite3'
        # and set TENANT_MAP_STRATEGY = 'single' in apps.tenants settings.
        # The recommended approach is a dedicated test PostgreSQL DB.
        'NAME': 'ebr_test',
        'USER': 'ebr_user',
        'PASSWORD': 'ebr_dev_password_2024',
        'HOST': 'localhost',
        'PORT': '5432',
        'TEST': {
            'NAME': 'ebr_test',
        },
    }
}

# Disable throttling in tests
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []

# Use console email backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable Celery in tests (run tasks eagerly)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# No CORS issues in tests
CORS_ALLOW_ALL_ORIGINS = True

# Disable logging noise in tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {'class': 'logging.NullHandler'},
    },
    'root': {
        'handlers': ['null'],
    },
}
