from contextvars import ContextVar
from contextlib import contextmanager
from django_omnitenant.constants import constants
from django_omnitenant.models import BaseTenant


class TenantContext:
    _current_tenant = ContextVar("current_tenant", default=None)
    _current_tenant_db_alias = ContextVar(
        "current_tenant_db_alias", default=constants.DEFAULT_DB_ALIAS
    )

    @classmethod
    def get_tenant(cls):
        return cls._current_tenant.get()

    @classmethod
    def set_tenant(cls, tenant):
        cls._current_tenant.set(tenant)

    @classmethod
    def clear_tenant(cls):
        cls._current_tenant.set(None)

    @classmethod
    def get_db_alias(cls):
        return cls._current_tenant_db_alias.get()

    @classmethod
    def set_db_alias(cls, db_alias):
        cls._current_tenant_db_alias.set(db_alias)

    @classmethod
    def clear_db_alias(cls):
        cls._current_tenant_db_alias.set(constants.DEFAULT_DB_ALIAS)

    @classmethod
    def clear_all(cls):
        cls.clear_tenant()
        cls.clear_db_alias()

    @classmethod
    @contextmanager
    def use(cls, tenant):
        from django_omnitenant.backends.database_backend import DatabaseTenantBackend
        from django_omnitenant.backends.schema_backend import SchemaTenantBackend

        """Activate a tenant context (schema or DB) for the duration of the context."""
        # Save previous tenant
        prev_token_tenant = cls._current_tenant.get()
        token_tenant = cls._current_tenant.set(tenant)

        # Activate backend
        backend = (
            SchemaTenantBackend(tenant)
            if tenant.isolation_type == BaseTenant.IsolationType.SCHEMA
            else DatabaseTenantBackend(tenant)
        )
        backend.activate()

        try:
            yield
        finally:
            # Deactivate backend and restore previous tenant
            backend.deactivate()
            cls._current_tenant.reset(token_tenant)
            cls._current_tenant.set(prev_token_tenant)
