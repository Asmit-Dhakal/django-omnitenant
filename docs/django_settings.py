SECRET_KEY = "docs"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django_omnitenant",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
