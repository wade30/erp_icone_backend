
"""
Django settings for ERP project.
Configuration compatible avec environnement local et Docker.
"""

from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
import dj_database_url

# ============================================================
# 1. CHEMINS DU PROJET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# 2. CHARGEMENT DU FICHIER .env
# ============================================================

env_file = BASE_DIR / ".env"
load_dotenv(env_file)

if env_file.is_file():
    env_lines = env_file.read_text(encoding="utf-8-sig").splitlines()

    for line_number, line in enumerate(env_lines, 1):
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        key, separator, value = line.partition("=")

        if not separator or not key.strip():
            raise ValueError(
                f"Invalid entry in {env_file} at line {line_number}"
            )

        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1]:
            if value[0] in ("'", '"'):
                value = value[1:-1]

        os.environ.setdefault(key.strip(), value)


# ============================================================
# 3. CONFIGURATION GENERALE ET SECURITE
# ============================================================

SECRET_KEY = os.environ.get("SECRET_KEY", "")

if not SECRET_KEY:
    raise ValueError("La variable SECRET_KEY est obligatoire.")

DEBUG = os.environ.get("DEBUG", "True").lower() in (
    "true", "1", "yes"
)


def get_env_list(name, default=""):
    return [
        value.strip()
        for value in os.environ.get(name, default).split(",")
        if value.strip()
    ]


ALLOWED_HOSTS = get_env_list(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1"
)

CSRF_TRUSTED_ORIGINS = get_env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174"
)


# ============================================================
# 4. APPLICATIONS DJANGO
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",

    "users",
    "finance",
    "accounting",
    "budgeting",
    "institute",
    "incubator",
    "marketing",
    "orientation",
    "preschool",
]

AUTH_USER_MODEL = "users.User"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# 5. MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# 6. CONFIGURATION CORS
# ============================================================

CORS_ALLOWED_ORIGINS = get_env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174"
)

CORS_ALLOW_CREDENTIALS = True


# ============================================================
# 7. URLS ET TEMPLATES
# ============================================================

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ============================================================
# 8. BASE DE DONNEES POSTGRESQL
# ============================================================


# Database
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL is not set in environment")

DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL)
}

DATABASES["default"]["CONN_MAX_AGE"] = 600
# ============================================================
# 9. VALIDATION DES MOTS DE PASSE
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# 10. LANGUE ET FUSEAU HORAIRE
# ============================================================

LANGUAGE_CODE = "fr-fr"

TIME_ZONE = "Africa/Dakar"

USE_I18N = True

USE_TZ = True


# ============================================================
# 11. FICHIERS STATIQUES ET MEDIAS
# ============================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# 12. EMAIL
# ============================================================

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}


# ============================================================
# 13. DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "users.permissions.ERPModulePermission",
    ],

    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],

    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),

    "PAGE_SIZE": 20,

    "DEFAULT_THROTTLE_RATES": {
        "registration": "5/hour",
    },
}


# ============================================================
# 14. CONFIGURATION DE LA COMPTABILISATION AUTOMATIQUE
# ============================================================

ACCOUNTING_AUTOMATION = {

    "receipt_journal_codes": {
        "BANK": "BQ",
        "CASH": "CA",
        "WAVE": "MP",
        "ORANGE_MONEY": "MP",
        "OTHER": "OD",
    },

    "expense_journal_codes": {
        "BANK": "BQ",
        "CASH": "CA",
        "WAVE": "MP",
        "ORANGE_MONEY": "MP",
        "OTHER": "OD",
    },

    "receipt_income_account_code": "706",

    "default_expense_account_code": "625",

    "payment_account_codes": {
        "CASH": "571",
        "WAVE": "585",
        "ORANGE_MONEY": "586",
        "OTHER": "588",
    },

    "bank_account_codes": {
        "1": "521",
        "2": "522",
    },

    "expense_category_account_codes": {
        "Transport": "624",
        "Communication": "626",
        "Fournitures": "605",
    },
}


# ============================================================
# 15. SECURITE HTTPS (ACTIVATION EN PRODUCTION)
# ============================================================

SECURE_SSL_REDIRECT = (
    os.environ.get("SECURE_SSL_REDIRECT", "False").lower()
    in ("true", "1", "yes")
)

SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SECURE = not DEBUG

if os.environ.get("USE_HTTPS_PROXY", "False").lower() in (
    "true", "1", "yes"
):
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https"
    )
