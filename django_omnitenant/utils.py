from django.apps import apps
from .conf import settings
from django.db.models.base import Model
from django.db import connections
from django.core.cache import caches
import re


def get_tenant_model() -> type[Model]:
    return apps.get_model(settings.TENANT_MODEL)


def get_domain_model() -> type[Model]:
    return apps.get_model(settings.DOMAIN_MODEL)


def get_custom_apps() -> list[str]:
    """
    Return a list of custom apps within the project (excluding built-in and third-party apps).
    """
    if hasattr(settings, "CUSTOM_APPS"):
        return settings.CUSTOM_APPS

    custom_apps = []
    base_dir_str = str(settings.BASE_DIR)

    for app_config in apps.get_app_configs():
        if app_config.path.startswith(base_dir_str):
            custom_apps.append(app_config.name)

    return custom_apps


def reset_db_connection(alias: str):
    """
    Close and evict a DB connection so the next access uses the updated
    settings.DATABASES[alias].
    """
    if alias in connections:
        try:
            connections[alias].close()
        except Exception:
            pass

        try:
            del connections._connections.connections[alias]  # type: ignore[attr-defined]
        except Exception:
            pass

    # Force re-initialization on demand
    return connections[alias]


def reset_cache_connection(alias: str):
    """
    Close and evict a cache client so the next access uses the updated
    settings.CACHES[alias].
    """
    # Best effort: if a backend exists already, close it.
    try:
        backend = caches._caches.caches.get(alias)  # type: ignore[attr-defined]
        if backend and hasattr(backend, "close"):
            try:
                backend.close()
            except Exception:
                pass
    except Exception:
        pass

    # Evict the cached backend so it will be rebuilt on next access
    try:
        caches._caches.caches.pop(alias, None)  # type: ignore[attr-defined]
    except Exception:
        pass

    # Force re-initialization on demand
    return caches[alias]


def convert_to_valid_pgsql_schema_name(name: str) -> str:
    """
    Convert a string into a valid PostgreSQL schema name.
    Rules:
      - Max length 63
      - Cannot start with 'pg_'
      - Only letters, numbers, and underscores
      - Lowercased
    """
    # Normalize: lowercase + replace invalid chars with underscore
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower())

    # Trim length to 63
    name = name[:63]

    # If starts with 'pg_', prefix with 'x_'
    if name.startswith("pg_"):
        name = f"x_{name[3:]}" or "x"

    # Ensure not empty
    if not name:
        name = "default_schema"

    return name


def get_active_schema_name(connection=None, db_alias: str | None = None) -> str:
    """
    Get the currently active schema name for the given database connection.
    If no connection is provided, uses the default connection.
    """
    if connection is None:
        connection = connections[db_alias or "default"]

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_schema();")
            return cursor.fetchone()[0]  # type: ignore
    except Exception:
        return "public"
