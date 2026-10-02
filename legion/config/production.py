from .base import *
from django.core.exceptions import ImproperlyConfigured
DEBUG=False
IS_STAGING=False
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
if '*' in ALLOWED_HOSTS or not DATABASES['default']['ENGINE'].endswith('postgresql'):
    raise ImproperlyConfigured('Production requires explicit ALLOWED_HOSTS and PostgreSQL.')
if SECRET_KEY.startswith(('replace-','development-')):
    raise ImproperlyConfigured('Production requires a generated secret.')
