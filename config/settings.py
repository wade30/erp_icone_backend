
"""
Django settings for ERP project.
Compatible avec :
- Développement local
- Docker
- Production Hostinger

Sécurité CSRF, CORS, sessions et HTTPS configurables.
"""

from pathlib import Path
import os

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
import dj_database_url


# ============================================================
# 1. CHEMINS DU PROJET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# 2. CHARGEMENT DU FICHIER .env
# ============================================================

env_file = BASE_DIR / ".env"
load_dotenv(env_file, override=False)


# ============================================================
# 3. FONCTIONS ENVIRONNEMENT
# ============================================================

def env_bool(name, default=False):
    return (
        os.environ.get(name, str(default))
        .strip()
        .lower()
        in ("true", "1", "yes", "on")
    )


def get_env_list(name, default=""):
    return [
        value.strip()
        for value in os.environ.get(name, default).split(",")
        if value.strip()
    ]


def get_env_value(name, default=None):
    value = os.environ.get(name, "")
    return value.strip() if value.strip() else default


# ============================================================
# 4. CONFIGURATION GENERALE
# ============================================================

DEBUG = env_bool("DEBUG", False)

SECRET_KEY = get_env_value("SECRET_KEY")

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "La variable SECRET_KEY est obligatoire."
    )

ALLOWED_HOSTS = get_env_list(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1"
)


# ============================================================
# 5. ORIGINES FRONTEND : CORS ET CSRF
# ============================================================

LOCAL_ORIGINS = (
    "http://localhost:5173,"
    "http://127.0.0.1:5173,"
    "http://localhost:5174,"
    "http://127.0.0.1:5174"
)

PRODUCTION_FRONTEND = (
    "https://erp-icone-frontend.vercel.app"
)

CSRF_TRUSTED_ORIGINS = get_env_list(
    "CSRF_TRUSTED_ORIGINS",
    (
        LOCAL_ORIGINS + ","
        + PRODUCTION_FRONTEND
    )
)

CORS_ALLOWED_ORIGINS = get_env_list(
    "CORS_ALLOWED_ORIGINS",
    (
        LOCAL_ORIGINS + ","
        + PRODUCTION_FRONTEND
    )
)

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]


# ============================================================
# 6. APPLICATIONS
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
# 7. MIDDLEWARE
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
# 8. URLS ET TEMPLATES
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
# 9. BASE DE DONNEES POSTGRESQL
# ============================================================

DATABASE_URL = get_env_value("DATABASE_URL")

if not DATABASE_URL:
    raise ImproperlyConfigured(
        "DATABASE_URL est obligatoire."
    )

DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL)
}

DATABASES["default"]["CONN_MAX_AGE"] = 600


# ============================================================
# 10. VALIDATION DES MOTS DE PASSE
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
# 11. LANGUE ET FUSEAU HORAIRE
# ============================================================

LANGUAGE_CODE = "fr-fr"

TIME_ZONE = "Africa/Dakar"

USE_I18N = True

USE_TZ = True


# ============================================================
# 12. FICHIERS STATIQUES ET MEDIAS
# ============================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# 13. EMAIL
# ============================================================

MAILERS = {
    "default": {
        "BACKEND": (
            "django.core.mail.backends.console.EmailBackend"
        ),
    },
}


# ============================================================
# 14. DJANGO REST FRAMEWORK
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
# 15. COMPTABILISATION AUTOMATIQUE
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
# 16. HTTPS ET PROXY HOSTINGER
# ============================================================

SECURE_SSL_REDIRECT = env_bool(
    "SECURE_SSL_REDIRECT",
    not DEBUG
)

if env_bool("USE_HTTPS_PROXY", not DEBUG):
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https"
    )


# ============================================================
# 17. COOKIES DE SESSION ET CSRF
# ============================================================

SESSION_COOKIE_SECURE = env_bool(
    "SESSION_COOKIE_SECURE",
    not DEBUG
)

CSRF_COOKIE_SECURE = env_bool(
    "CSRF_COOKIE_SECURE",
    not DEBUG
)

# Le token est transmis par la réponse JSON CSRF.
# JavaScript n'a donc pas besoin de lire le cookie.
CSRF_COOKIE_HTTPONLY = True

SESSION_COOKIE_HTTPONLY = True

# Vercel et Hostinger sont des sites différents.
# None est nécessaire pour les cookies cross-site.
SESSION_COOKIE_SAMESITE = "None"

CSRF_COOKIE_SAMESITE = "None"

# Cookies limités au domaine de l'API.
CSRF_COOKIE_DOMAIN = None

SESSION_COOKIE_DOMAIN = None

CSRF_COOKIE_AGE = 60 * 60 * 24 * 7

SESSION_COOKIE_AGE = 60 * 60 * 8

SESSION_SAVE_EVERY_REQUEST = True

SESSION_EXPIRE_AT_BROWSER_CLOSE = False

CSRF_USE_SESSIONS = False

CSRF_FAILURE_VIEW = "django.views.csrf.csrf_failure"


# ============================================================
# 18. SECURITE HTTP
# ============================================================

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

SECURE_REFERRER_POLICY = "same-origin"

if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False


# ============================================================
# 19. VERIFICATIONS DE CONFIGURATION
# ============================================================

if not DEBUG:

    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS doit être configuré en production."
        )

    if not CORS_ALLOWED_ORIGINS:
        raise ImproperlyConfigured(
            "CORS_ALLOWED_ORIGINS doit être configuré en production."
        )

    if not CSRF_TRUSTED_ORIGINS:
        raise ImproperlyConfigured(
            "CSRF_TRUSTED_ORIGINS doit être configuré en production."
        )

    if not CORS_ALLOW_CREDENTIALS:
        raise ImproperlyConfigured(
            "CORS_ALLOW_CREDENTIALS doit être activé."
        )

    if not CSRF_COOKIE_SECURE or not SESSION_COOKIE_SECURE:
        raise ImproperlyConfigured(
            "Les cookies doivent être sécurisés en production."
        )

    if (
        SESSION_COOKIE_SAMESITE != "None"
        or CSRF_COOKIE_SAMESITE != "None"
    ):
        raise ImproperlyConfigured(
            "SameSite=None est requis pour les cookies cross-site."
        )
