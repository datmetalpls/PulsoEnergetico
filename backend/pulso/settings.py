import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse, unquote

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver,web').split(',')
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
                  'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'energy']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
              'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
              'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
              'django.contrib.messages.middleware.MessageMiddleware']
ROOT_URLCONF = 'pulso.urls'
WSGI_APPLICATION = 'pulso.wsgi.application'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True,
              'OPTIONS': {'context_processors': ['django.template.context_processors.request',
                  'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
db = urlparse(os.getenv('DATABASE_URL', ''))
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql',
    'NAME': unquote(db.path.lstrip('/')) if db.scheme else os.getenv('POSTGRES_DB', 'pulso'),
    'USER': unquote(db.username or '') if db.scheme else os.getenv('POSTGRES_USER', 'pulso'),
    'PASSWORD': unquote(db.password or '') if db.scheme else os.environ['POSTGRES_PASSWORD'],
    'HOST': db.hostname if db.scheme else os.getenv('POSTGRES_HOST', 'db'),
    'PORT': db.port if db.scheme else os.getenv('POSTGRES_PORT', '5432')}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'es-cl'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
WHITENOISE_ROOT = os.getenv('SPA_ROOT', str(BASE_DIR.parent / 'frontend/dist/pulso/browser'))
CSRF_FAILURE_VIEW = 'energy.views.csrf_failure'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
CACHES = {'default': {
    'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
    'LOCATION': os.getenv('CACHE_DIR', str(Path(tempfile.gettempdir()) / 'pulso-cache')),
}}
LOGIN_RATE_LIMIT = int(os.getenv('LOGIN_RATE_LIMIT', '5'))
LOGIN_RATE_WINDOW_S = int(os.getenv('LOGIN_RATE_WINDOW_S', '60'))
