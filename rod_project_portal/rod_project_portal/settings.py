from pathlib import Path
from django.urls import reverse_lazy
from dotenv import load_dotenv
import os

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
INTERNAL_IPS = ["127.0.0.1"]

if DEBUG:
    import socket

    try:
        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
        INTERNAL_IPS.append("10.0.2.2")
        INTERNAL_IPS.extend([ip[: ip.rfind(".")] + ".1" for ip in ips])
    except socket.gaierror:
        pass

    REDIS_HOST = "127.0.0.1"
else:
    REDIS_HOST = "portal_redis"

ALLOWED_HOSTS = [
                    "localhost",
                    "0.0.0.0",
                    "127.0.0.1",
                ] + os.getenv(
    "DJANGO_ALLOWED_HOSTS", ""
).split(",")

CSRF_TRUSTED_ORIGINS = [
    "https://rod-project.24-7.ro",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_ratelimit",
    "accounts.apps.AuthConfig",
    "youtube.apps.YoutubeConfig",
    "calls.apps.CallsConfig",
    "widget_tweaks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "rod_project_portal.urls"

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
                "accounts.utils.unread_notifications_count",
                "accounts.utils.is_superuser",
            ],
        },
    },
]

ASGI_APPLICATION = "rod_project_portal.asgi.application"

db_dir = BASE_DIR / "db"
db_dir.mkdir(exist_ok=True)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db" / "db.sqlite3",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, 6379)],
        },
    },
}

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

LANGUAGE_CODE = "ru-RU"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"

# for Debug = True
STATICFILES_DIRS = [
    BASE_DIR / "static_debug",
    # BASE_DIR / 'rod_project_portal/static',
]

LOGIN_REDIRECT_URL = reverse_lazy("accounts:main")
LOGIN_URL = "login/"

# Хранение сессии 24 часов
# Окончание сессии при закрытии браузера отключено
SESSION_COOKIE_AGE = 60 * 60 * 24
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

APPEND_SLASH = True

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT")

######## Add in Caddy file ########
# Rod project portal
# https://rod-project.24-7.ro {
#     encode zstd gzip
#     reverse_proxy rod_project_portal_container:8000
# }

# SECURE_SSL_REDIRECT не включать


if not DEBUG:
    # Caddy передаёт X-Forwarded-Proto: без этой строки Django считает запросы http
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

TURN_SECRET = os.getenv("TURN_SECRET", "")
TURN_HOST = os.getenv("TURN_HOST", "")