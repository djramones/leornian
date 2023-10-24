"""Django settings for leornian project."""

from pathlib import Path
from email.utils import parseaddr

from django.contrib.messages import constants as messages

import environ


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("LEOR_SECRET_KEY")
DEBUG = env.bool("LEOR_DEBUG")
ALLOWED_HOSTS = env.list("LEOR_ALLOWED_HOSTS")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": env("LEOR_DB_HOST"),
        "PORT": env("LEOR_DB_PORT"),
        "NAME": env("LEOR_DB_NAME"),
        "USER": env("LEOR_DB_USER"),
        "PASSWORD": env("LEOR_DB_PASSWORD"),
    }
}


# Application definition

INSTALLED_APPS = [
    "notes.apps.NotesConfig",
    "support.apps.SupportConfig",
    "moderation.apps.ModerationConfig",
    "crispy_forms",
    "crispy_bootstrap5",
    "formtools",
    "django_registration",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "leornian.urls"
ABSOLUTE_URL_OVERRIDES = {
    "auth.user": lambda o: f"/@{o.username}/",
}
WSGI_APPLICATION = "leornian.wsgi.application"

if DEBUG:
    # Debug Toolbar
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1"]

# Models

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Templates

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "leornian.context_processors.colormode",
            ],
            "debug": DEBUG,  # for django-coverage-plugin
        },
    },
]
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# Messages

MESSAGE_TAGS = {
    messages.DEBUG: "alert-secondary",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}


# Authentication

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
LOGIN_REDIRECT_URL = LOGOUT_REDIRECT_URL = "home"

# django-registration:
ACCOUNT_ACTIVATION_DAYS = 7
REGISTRATION_OPEN = env.bool("LEOR_REG_OPEN")


# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files

STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "static-collected"
STATIC_URL = "static/"


# Captcha

CAPTCHA_SITE_KEY = env("LEOR_CAPTCHA_SITE_KEY")
CAPTCHA_SECRET_KEY = env("LEOR_CAPTCHA_SECRET_KEY")


# Email

DEFAULT_FROM_EMAIL = env("LEOR_DEFAULT_FROM_EMAIL")
SERVER_EMAIL = env("LEOR_SERVER_EMAIL")
ADMINS = list(parseaddr(email) for email in env("LEOR_ADMINS").split(","))
EMAIL_SUBJECT_PREFIX = "[Leornian] "
if env.bool("LEOR_EMAIL_LOCAL_DEV"):
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_HOST = env("LEOR_EMAIL_HOST")
    EMAIL_PORT = env.int("LEOR_EMAIL_PORT")
    EMAIL_HOST_USER = env("LEOR_EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("LEOR_EMAIL_HOST_PASSWORD")
    EMAIL_USE_TLS = env.bool("LEOR_EMAIL_USE_TLS")
