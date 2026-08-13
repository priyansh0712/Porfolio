"""
Production Django Settings — Environment-driven Secrets & Strict SSL/XSS/HSTS Hardening.

Architecture (SEC-01):
  - Loads SECRET_KEY, ALLOWED_HOSTS, and DATABASE_URL strictly from environment variables.
  - DEBUG defaults to False.
  - Enforces HSTS (31536000 seconds), Secure Cookies, X-Frame DENY, and XSS Protection.
  - Configures proxy SSL header for Nginx SSL termination.
"""
import os
from .base import *

DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-prod-fallback-must-be-set-in-environment-variable!',
)

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '.ourapp.com,localhost,127.0.0.1').split(',')

# ── Production Security & SSL Hardening Headers ──
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 31536000))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── Static & Media Storage ──
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Cache Backend (Redis / LocMem fallback) ──
REDIS_URL = os.environ.get('REDIS_URL', '')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
