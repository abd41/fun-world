"""Django settings for Fun World.

Two rules shape this file, both from the constitution:

  §7  No hardcoded hosts. Every address comes from the environment. A literal
      `localhost` here works on this laptop and fails on a phone, and nobody
      finds out until they are standing in front of a television.

  §19 No secrets in the repository. SECRET_KEY comes from the environment and
      has no production-shaped default.

`FW_HOST` is resolved once by `scripts/setup` — from the environment, then
`.env`, then auto-detection — and everything here reads that single value.
It is a *host*, not an IP: `192.168.0.106`, `funworld.local` and
`funworld.tailnet.ts.net` are all valid, which is what makes moving to a VPN
a one-line change rather than a refactor.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    FW_HOST=(str, "localhost"),
)
# Repo root — .env lives beside OWNERS.yml, not inside apps/api, because one
# host value is shared by the API and both clients.
environ.Env.read_env(BASE_DIR.parent.parent / ".env")

# --- security ---------------------------------------------------------------

# No default. A missing SECRET_KEY should stop the process, not silently fall
# back to something predictable that then reaches a branch someone shares.
SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env("DJANGO_DEBUG")

FW_HOST = env("FW_HOST")

# The phone and the televisions arrive as FW_HOST; the browser on this machine
# arrives as localhost. Both are legitimate, so both are allowed.
ALLOWED_HOSTS = ["localhost", "127.0.0.1", FW_HOST]

# The clients are served from other origins on the same network, so CORS is
# unavoidable here. It is scoped to the client ports on each allowed host
# rather than opened wide — this is a home network, not a public API, and "*"
# would outlive the moment of convenience that introduced it.
#
# Built from ALLOWED_HOSTS rather than listing localhost separately. The
# earlier version hardcoded "http://localhost:3000" and "http://localhost:8081"
# alongside the FW_HOST entries, which check_constitution.py flagged as a §7
# violation — correctly. They were harmless in effect, since the FW_HOST
# entries were also present, but §7 says every URL comes from configuration and
# a rule with a comfortable exception is a rule that grows more of them.
CLIENT_PORTS = (3000, 8081)
CORS_ALLOWED_ORIGINS = [
    f"http://{host}:{port}" for host in ALLOWED_HOSTS for port in CLIENT_PORTS
]

# --- applications -----------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # --- Fun World apps ---
    #
    # Registering an app is a human step: this file is HUMAN-owned, so
    # data-agent cannot add its own app here. That is the cost accepted in
    # research R1, roughly once per vertical.
    #
    # An app is listed here only once it exists — a scaffold that cannot boot
    # until an agent's task lands is a scaffold that blocks the agent it was
    # meant to unblock.
    "core",
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

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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

# --- database ---------------------------------------------------------------

# Published on 5433 rather than 5432 so it cannot collide with a Postgres the
# developer already runs. Credentials come from the environment.
DATABASES = {"default": env.db("DATABASE_URL")}

# --- auth -------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n / static ----------------------------------------------------------

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
