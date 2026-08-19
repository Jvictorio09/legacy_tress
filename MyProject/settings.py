"""
Django settings for MyProject.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env locally (OPENAI_API_KEY, etc.) — file is gitignored.
_env_file = BASE_DIR / '.env'
if _env_file.exists():
    for line in _env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

# SECURITY WARNING: keep the secret key used in production secret!
# Set DJANGO_SECRET_KEY in the Railway dashboard for production.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY', 'django-insecure-change-me-in-production'
)

# Debug is on locally, automatically off once running on Railway.
DEBUG = 'RAILWAY_ENVIRONMENT' not in os.environ

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'legacytress-production.up.railway.app',
    'legacytress.com',
    'www.legacytress.com',
]
# Railway injects the live public domain at runtime — trust it automatically.
RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if RAILWAY_PUBLIC_DOMAIN and RAILWAY_PUBLIC_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

# HTTPS origins allowed to submit forms / log into the admin.
CSRF_TRUSTED_ORIGINS = [
    'https://legacytress-production.up.railway.app',
    'https://legacytress.com',
    'https://www.legacytress.com',
]
if RAILWAY_PUBLIC_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RAILWAY_PUBLIC_DOMAIN}')

# Locally, accept any host so runserver / tests work without fuss.
if DEBUG:
    ALLOWED_HOSTS = ['*']

# Production-only HTTPS hardening (Railway terminates TLS at its proxy).
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'MyApp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'MyProject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.csrf',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'MyProject.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise serves compressed, cache-busted static files in production.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Trust Railway's proxy for HTTPS detection.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Phone selfies can exceed Django's 2.5 MB default; the try-on view caps at 10 MB.
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024

# API endpoints should get JSON, not Django's HTML 403 page.
CSRF_FAILURE_VIEW = 'MyApp.views.csrf_failure'

# AI Ethereal Boho preview (OpenAI)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_IMAGE_MODEL = os.environ.get('OPENAI_IMAGE_MODEL', 'gpt-image-1')
BOHO_STYLE_REFERENCE_URL = os.environ.get('BOHO_STYLE_REFERENCE_URL', (
    'https://images.leadconnectorhq.com/image/f_webp/q_80/r_1200/u_https://'
    'assets.cdn.filesafe.space/PdsP45Yo0hioveq4oKF8/media/69150d324a60b5912d8e4bb0.jpg'
))

# AI Hair Concierge (OpenAI chat + realtime voice)
OPENAI_CHAT_MODEL = os.environ.get('OPENAI_CHAT_MODEL', 'gpt-4o-mini')
OPENAI_REALTIME_MODEL = os.environ.get('OPENAI_REALTIME_MODEL', 'gpt-realtime')
# Warm female voice for the concierge (GA realtime voices include coral, shimmer, sage, marin).
OPENAI_CONCIERGE_VOICE = os.environ.get('OPENAI_CONCIERGE_VOICE', 'coral')
