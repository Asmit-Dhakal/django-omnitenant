from contextvars import ContextVar
from contextlib import contextmanager
from django_omnitenant.constants import constants


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
        cls._current_tenant_db_alias.set(None)

    @classmethod
    def clear_all(cls):
        cls.clear_tenant()
        cls.clear_db_alias()

    @classmethod
    @contextmanager
    def use(cls, tenant=None, db_alias=None):
        # Save previous state
        token_tenant = cls._current_tenant.set(tenant) if tenant is not None else None
        token_db = (
            cls._current_tenant_db_alias.set(db_alias) if db_alias is not None else None
        )
        try:
            yield
        finally:
            # Restore old state if changed
            if token_tenant is not None:
                cls._current_tenant.reset(token_tenant)
            if token_db is not None:
                cls._current_tenant_db_alias.reset(token_db)
