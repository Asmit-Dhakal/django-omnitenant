from contextvars import ContextVar
from contextlib import contextmanager
from django_omnitenant.constants import constants
from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_model


class TenantContext:
    _tenant_stack = ContextVar("tenant_stack", default=[])
    _db_alias_stack = ContextVar("db_alias_stack", default=[constants.DEFAULT_DB_ALIAS])
    _cache_alias_stack = ContextVar(
        "cache_alias_stack", default=[constants.DEFAULT_CACHE_ALIAS]
    )

    # --- Tenant ---
    @classmethod
    def get_tenant(cls):
        stack = cls._tenant_stack.get()
        return stack[-1] if stack else None

    @classmethod
    def push_tenant(cls, tenant):
        stack = cls._tenant_stack.get()
        new_stack = stack + [tenant]
        cls._tenant_stack.set(new_stack)

    @classmethod
    def pop_tenant(cls):
        stack = cls._tenant_stack.get()
        if stack:
            new_stack = stack[:-1]
            cls._tenant_stack.set(new_stack)

    # --- Database ---
    @classmethod
    def get_db_alias(cls):
        stack = cls._db_alias_stack.get()
        return stack[-1] if stack else constants.DEFAULT_DB_ALIAS

    @classmethod
    def push_db_alias(cls, db_alias):
        stack = cls._db_alias_stack.get()
        new_stack = stack + [db_alias]
        cls._db_alias_stack.set(new_stack)

    @classmethod
    def pop_db_alias(cls):
        stack = cls._db_alias_stack.get()
        if stack:
            new_stack = stack[:-1]
            cls._db_alias_stack.set(new_stack)

    # --- Cache ---
    @classmethod
    def get_cache_alias(cls):
        stack = cls._cache_alias_stack.get()
        return stack[-1] if stack else "default"

    @classmethod
    def push_cache_alias(cls, cache_alias):
        stack = cls._cache_alias_stack.get()
        new_stack = stack + [cache_alias]
        cls._cache_alias_stack.set(new_stack)

    @classmethod
    def pop_cache_alias(cls):
        stack = cls._cache_alias_stack.get()
        if stack:
            new_stack = stack[:-1]
            cls._cache_alias_stack.set(new_stack)

    # --- Clear all (reset to defaults) ---
    @classmethod
    def clear_all(cls):
        cls._tenant_stack.set([])
        cls._db_alias_stack.set([constants.DEFAULT_DB_ALIAS])
        cls._cache_alias_stack.set(["default"])

    # --- Context manager ---
    @classmethod
    @contextmanager
    def use_tenant(cls, tenant):
        from django_omnitenant.backends.database_backend import DatabaseTenantBackend
        from django_omnitenant.backends.schema_backend import SchemaTenantBackend
        from django_omnitenant.backends.cache_backend import CacheTenantBackend

        # Push tenant
        cls.push_tenant(tenant)

        # Activate DB/Schema backend
        backend = (
            SchemaTenantBackend(tenant)
            if tenant.isolation_type == BaseTenant.IsolationType.SCHEMA
            else DatabaseTenantBackend(tenant)
        )
        backend.activate()
        cls.push_db_alias(cls.get_db_alias())  # backend may change alias

        # Activate cache backend
        cache_backend = CacheTenantBackend(tenant)
        cache_backend.activate()
        cls.push_cache_alias(cls.get_cache_alias())

        try:
            yield
        finally:
            # Deactivate backends
            backend.deactivate()
            cache_backend.deactivate()

            # Pop tenant/db/cache
            cls.pop_tenant()
            cls.pop_db_alias()
            cls.pop_cache_alias()

    @classmethod
    @contextmanager
    def use_schema(cls, schema_name: str):
        """
        Context manager to use a specific schema.
        """
        from django_omnitenant.backends.schema_backend import SchemaTenantBackend

        tenant: BaseTenant = get_tenant_model()(tenant_id=schema_name)  # type: ignore # Mock tenant for context
        backend = SchemaTenantBackend(tenant)
        backend.activate()

        try:
            yield
        finally:
            backend.deactivate()
            cls.pop_db_alias()
