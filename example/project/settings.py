"""Minimal settings for the django-spaserve example project.

Demonstrates Strategy A (catch-all `spa_urls`) which serves both the built assets
and the SPA shell fallback itself — the simplest setup to run with `runserver`.
No database / auth apps are needed just to serve a SPA.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Where the built React app lands (see ../frontend, `npm run build`).
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

SECRET_KEY = "example-only-not-secret"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django_spaserve",  # enables `manage.py check` validation of the mount
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {"context_processors": []},
    }
]

WSGI_APPLICATION = "project.wsgi.application"

# This example uses no database.
DATABASES = {}

USE_TZ = True

# --- Strategy B (production) reference -------------------------------------
# In production you would let WhiteNoise/CDN serve the hashed assets and use the
# handler404 fallback instead. To try it: comment out the spa_urls() line in
# urls.py, set `handler404 = "django_spaserve.handler404"` there, and uncomment:
#
# DJANGO_SPASERVE = [
#     {"prefix": "/", "directory": FRONTEND_DIST, "fallback": "index.html"},
# ]
