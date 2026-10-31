import os
import secrets
import sys
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Use one explicit project-local file for manage.py, WSGI and ASGI.
# Deployment environment variables always take precedence over this optional file.
load_dotenv(BASE_DIR.parent / ".env", override=False)

def _env_list(name, default=""):
    return [value.strip() for value in os.environ.get(name, default).split(",") if value.strip()]


DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ("true", "1")
# A generated fallback prevents an accidentally committed development key from
# being used in production. Deployments should always set DJANGO_SECRET_KEY so
# sessions and signed values survive a restart.
_configured_secret = os.environ.get("DJANGO_SECRET_KEY")
_legacy_example_secret = "kanban-secret-key-super-secure-jwt-2026-production"
_has_configured_secret = bool(_configured_secret and _configured_secret != _legacy_example_secret)
# Tests need an isolated signing key but must never make a production process
# silently rotate JWT/signing secrets on restart.
if not DEBUG and not _has_configured_secret and "test" not in sys.argv:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be configured when DJANGO_DEBUG is false")
SECRET_KEY = _configured_secret if _has_configured_secret else secrets.token_urlsafe(64)

# Password onboarding is intentionally disabled unless delivery is configured
# in production.  This prevents activating an HR workflow that cannot safely
# deliver a one-time secret to the employee.
ONBOARDING_EMAIL_REQUIRED = os.environ.get("ONBOARDING_EMAIL_REQUIRED", "False").lower() in ("true", "1")
if ONBOARDING_EMAIL_REQUIRED and not os.environ.get("EMAIL_HOST"):
    raise ImproperlyConfigured("EMAIL_HOST is required when onboarding email delivery is enabled")

# ALLOWED_HOSTS is retained as a compatibility alias for existing deployments.
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"))

INSTALLED_APPS = [
    "daphne",
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "channels",
    "backend.infrastructure.persistence",
]

AUTH_USER_MODEL = "persistence.UserModel"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "backend.presentation.middlewares.JWTAuthenticationMiddleware",
]

ROOT_URLCONF = "backend.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.config.wsgi.application"
ASGI_APPLICATION = "backend.config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Database: SQLite default, configurable to Postgres
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "kanban_db"),
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.environ.get("POSTGRES_HOST", "db"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS: opt in to each browser origin instead of accepting credentials from any
# website. The local Next.js origins are useful for development and can be
# replaced with CORS_ALLOWED_ORIGINS in deployment.
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3001,http://127.0.0.1:3001")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_HEADERS = ["accept", "accept-encoding", "authorization", "content-type", "dnt", "origin", "user-agent", "x-csrftoken", "x-requested-with"]

# Jazzmin Admin Theme Configuration
JAZZMIN_SETTINGS = {
    "site_title": "Yrys Kanban Admin",
    "site_header": "Yrys Kanban",
    "site_brand": "Yrys Kanban",
    "welcome_sign": "Панель управления корпоративным Канбаном",
    "copyright": "Yrys Kanban Ltd",
    "search_model": "persistence.UserModel",
    "topmenu_links": [
        {"name": "Главная", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Канбан-доска (Веб)", "url": "http://localhost:3001", "new_window": True},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "auth": "fas fa-users-cog",
        "persistence.UserModel": "fas fa-user-tie",
        "persistence.DepartmentModel": "fas fa-building",
        "persistence.BoardModel": "fas fa-columns",
        "persistence.BoardMemberModel": "fas fa-id-badge",
        "persistence.ColumnModel": "fas fa-list-ul",
        "persistence.CardModel": "fas fa-tasks",
        "persistence.CardAssigneeModel": "fas fa-user-check",
        "persistence.ChecklistModel": "fas fa-check-square",
        "persistence.CommentModel": "fas fa-comments",
        "persistence.AttachmentModel": "fas fa-paperclip",
        "persistence.ActivityLogModel": "fas fa-history",
        "persistence.NotificationModel": "fas fa-bell",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": True,
    "changeform_format": "horizontal_tabs",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-primary",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "theme": "default",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}
