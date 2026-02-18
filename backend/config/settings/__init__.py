"""
Django settings package for EBR Platform.

Import the appropriate settings based on environment:
- development: Local development
- staging: Staging environment
- production: Production environment
"""
import os

environment = os.environ.get('DJANGO_ENVIRONMENT', 'development')

if environment == 'production':
    from .production import *
elif environment == 'staging':
    from .staging import *
else:
    from .development import *
