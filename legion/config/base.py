import os
from pathlib import Path
from urllib.parse import urlparse, unquote

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(os.getenv('LEGION_ENV_FILE') or BASE_DIR / '.env')

def flag(name, default=False):
    return os.getenv(name, str(default)).lower() in ('true', '1', 'yes')

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = flag('DEBUG', ENVIRONMENT == 'development')
IS_STAGING = ENVIRONMENT != 'production'
SECRET_KEY = os.getenv('SECRET_KEY', 'development-only-legion-key-change-before-deploy')
if ENVIRONMENT != 'development' and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith(('development','replace-'))):
    raise ImproperlyConfigured('Set a unique SECRET_KEY of at least 50 characters.')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
SITE_URL = os.getenv('SITE_URL', 'https://legionautorent.kz').rstrip('/')
CSRF_TRUSTED_ORIGINS = [x for x in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if x]

INSTALLED_APPS = ['core.admin_site.LegionAdminConfig', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'axes', 'core', 'locations', 'cars', 'pages', 'seo', 'bookings', 'analytics', 'importer']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.middleware.gzip.GZipMiddleware', 'core.middleware.CanonicalHostMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'core.i18n.LegionLocaleMiddleware', 'core.middleware.SelectedCityMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'axes.middleware.AxesMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware', 'analytics.middleware.AttributionMiddleware', 'seo.middleware.SEOMiddleware', 'core.middleware.ContentSecurityPolicyMiddleware']
ROOT_URLCONF = 'legion.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.debug', 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages', 'core.context.site_context']}}]
WSGI_APPLICATION = 'legion.wsgi.application'
db_url = os.getenv('DATABASE_URL', '')
if db_url:
    db = urlparse(db_url)
    if db.scheme not in ('postgres', 'postgresql'): raise ImproperlyConfigured('DATABASE_URL must be PostgreSQL.')
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': unquote(db.path.lstrip('/')), 'USER': unquote(db.username or ''), 'PASSWORD': unquote(db.password or ''), 'HOST': db.hostname, 'PORT': db.port or 5432, 'CONN_MAX_AGE': 60, 'OPTIONS': {'sslmode': os.getenv('DB_SSLMODE', 'prefer')}}}
else:
    if ENVIRONMENT != 'development': raise ImproperlyConfigured('PostgreSQL DATABASE_URL is required outside development.')
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

# Shared database cache makes spam limits consistent across Gunicorn workers.
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.db.DatabaseCache', 'LOCATION': 'legion_cache', 'TIMEOUT': 300}}
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'ru'
LANGUAGES = [('ru', 'Русский'), ('kk', 'Қазақша'), ('en', 'English')]
TIME_ZONE = 'Asia/Qyzylorda'
USE_I18N = True
LOCALE_PATHS = [BASE_DIR / 'locale']
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
APPEND_SLASH = False
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SECURE_SSL_REDIRECT = flag('SECURE_SSL_REDIRECT', ENVIRONMENT != 'development')
SECURE_REDIRECT_EXEMPT = [r'^healthz/$']
SESSION_COOKIE_SECURE = ENVIRONMENT != 'development'
CSRF_COOKIE_SECURE = ENVIRONMENT != 'development'
SECURE_HSTS_SECONDS = 31536000 if ENVIRONMENT == 'production' else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = ENVIRONMENT == 'production'
SECURE_HSTS_PRELOAD = ENVIRONMENT == 'production'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
HOSTING_PLATFORM = os.getenv('HOSTING_PLATFORM', 'generic')
CANONICAL_HOST_REDIRECT = flag('CANONICAL_HOST_REDIRECT', False)
SECURE_SSL_HOST = urlparse(SITE_URL).netloc if CANONICAL_HOST_REDIRECT else None
ADMIN_PATH = os.getenv('ADMIN_PATH','control-legion/').strip('/')+'/'
KAZAKH_PREFIX = '/kk'
PAGE_CACHE_TIMEOUT = int(os.getenv('PAGE_CACHE_TIMEOUT','60'))
AUTHENTICATION_BACKENDS = ['axes.backends.AxesStandaloneBackend','django.contrib.auth.backends.ModelBackend']
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = [['username','ip_address']]
AXES_RESET_ON_SUCCESS = True
AXES_CLIENT_IP_CALLABLE = 'bookings.spam.client_ip'
AXES_LOCKOUT_TEMPLATE = 'admin/locked.html'
ANALYTICS_ENABLED = flag('ANALYTICS_ENABLED') and ENVIRONMENT == 'production'
TRUST_PROXY_HEADERS = flag('TRUST_PROXY_HEADERS', ENVIRONMENT != 'development')
TRUSTED_PROXY_IPS = os.getenv('TRUSTED_PROXY_IPS','127.0.0.1,::1').split(',')
LOGGING = {'version': 1, 'disable_existing_loggers': False, 'handlers': {'console': {'class': 'logging.StreamHandler'}}, 'loggers': {'django': {'handlers': ['console'], 'level': 'WARNING'}, 'legion': {'handlers': ['console'], 'level': 'INFO'}}}
