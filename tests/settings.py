SECRET_KEY = "test-secret-key"
DEBUG = False
ALLOWED_HOSTS = ["*", "testserver"]

INSTALLED_APPS = [
    "django_spaserve",
]

MIDDLEWARE = []

ROOT_URLCONF = "tests.urls_empty"

DATABASES = {}

USE_TZ = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {"context_processors": []},
    }
]
