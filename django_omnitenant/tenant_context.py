from contextvars import ContextVar
from contextlib import contextmanager
from django_omnitenant.constants import constants
from django_omnitenant.models import BaseTenant


class TenantContext:
    _current_tenant = ContextVar("current_tenant", default=None)
    _current_tenant_db_alias = ContextVar(
        "current_tenant_db_alias", default=constants.DEFAULT_DB_ALIAS
    )
    _current_tenant_cache_alias = ContextVar(
        "current_tenant_cache_alias", default="default"
    )

    # --- Tenant ---
    @classmethod
    def get_tenant(cls):
        return cls._current_tenant.get()

    @classmethod
    def set_tenant(cls, tenant):
        cls._current_tenant.set(tenant)

    @classmethod
    def clear_tenant(cls):
        cls._current_tenant.set(None)

    # --- Database ---
    @classmethod
    def get_db_alias(cls):
        return cls._current_tenant_db_alias.get()

    @classmethod
    def set_db_alias(cls, db_alias):
        cls._current_tenant_db_alias.set(db_alias)

    @classmethod
    def clear_db_alias(cls):
        cls._current_tenant_db_alias.set(constants.DEFAULT_DB_ALIAS)

    # --- Cache ---
    @classmethod
    def get_cache_alias(cls):
        return cls._current_tenant_cache_alias.get()

    @classmethod
    def set_cache_alias(cls, cache_alias):
        cls._current_tenant_cache_alias.set(cache_alias)

    @classmethod
    def clear_cache_alias(cls):
        cls._current_tenant_cache_alias.set("default")

    # --- Clear all ---
    @classmethod
    def clear_all(cls):
        cls.clear_tenant()
        cls.clear_db_alias()
        cls.clear_cache_alias()

    # --- Context manager ---
    @classmethod
    @contextmanager
    def use(cls, tenant):
        from django_omnitenant.backends.database_backend import DatabaseTenantBackend
        from django_omnitenant.backends.schema_backend import SchemaTenantBackend
        from django_omnitenant.backends.cache_backend import CacheTenantBackend

        """Activate tenant context (DB, schema, cache) for duration of context."""
        # Save previous tokens
        prev_token_tenant = cls._current_tenant.get()
        token_tenant = cls._current_tenant.set(tenant)

        # Activate DB/Schema backend
        backend = (
            SchemaTenantBackend(tenant)
            if tenant.isolation_type == BaseTenant.IsolationType.SCHEMA
            else DatabaseTenantBackend(tenant)
        )
        backend.activate()

        # Activate cache backend
        cache_backend = CacheTenantBackend(tenant)
        cache_backend.activate()

        try:
            yield
        finally:
            # Deactivate backends
            backend.deactivate()
            cache_backend.deactivate()

            # Restore previous context
            cls._current_tenant.reset(token_tenant)
            cls._current_tenant.set(prev_token_tenant)
