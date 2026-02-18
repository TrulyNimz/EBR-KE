"""
Staging settings for EBR Platform.
"""
from .production import *

# Slightly relaxed settings for staging
DEBUG = False

# Allow staging domain
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'staging.ebr-platform.com').split(',')

# Logging
LOGGING['loggers']['apps']['level'] = 'DEBUG'
