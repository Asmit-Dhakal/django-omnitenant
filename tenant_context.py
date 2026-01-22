"""Tenant context helpers.

This module provides a thread-safe context for tracking the "current"
tenant, database alias and cache alias using Python's :mod:`contextvars`.

It exposes the :class:`TenantContext` helper which maintains per-context
stacks for tenant, database alias and cache alias values and offers
convenience context managers to temporarily switch to a tenant, the
master database, a public schema, or an arbitrary schema.

These utilities are intended for use by code that must run under a
specific tenant/environment (for example during request handling,
management commands or background tasks).

Example:
    with TenantContext.use_tenant(my_tenant):
        # code here runs with DB/cache backends activated for my_tenant
        ...
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional

from django_omnitenant.conf import settings
from django_omnitenant.constants import constants
from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_model


class TenantContext:
    """A context manager for tenant, database and cache selection.

    TenantContext stores three independent per-context stacks backed by
    :class:`contextvars.ContextVar`:

    - tenant stack: the active tenant objects
    - db alias stack: the active Django DB alias to use
    - cache alias stack: the active cache alias to use

    The stacks behave like simple lists: callers push a value before
    entering a temporary context and pop it when leaving. Several
    convenience context managers are provided to activate/deactivate
    tenant-related backends when switching contexts.
    """

    _tenant_stack = ContextVar("tenant_stack", default=[])
    _db_alias_stack = ContextVar("db_alias_stack", default=[settings.MASTER_DB_ALIAS])
    _cache_alias_stack = ContextVar(
        "cache_alias_stack", default=[settings.MASTER_DB_ALIAS]
    )

    # --- Tenant ---
    @classmethod
    def get_tenant(cls) -> Optional[BaseTenant]:
        """Return the current tenant or ``None`` if no tenant set.

        The current tenant is the top element of the tenant stack for the
        current context.
        """

        stack = cls._tenant_stack.get()
        return stack[-1] if stack else None

    @classmethod
    def push_tenant(cls, tenant: BaseTenant):
        """Push ``tenant`` onto the current context's tenant stack.

        Args:
            tenant: an instance of :class:`BaseTenant` to become active.
        """

        stack = cls._tenant_stack.get()
        new_stack = stack + [tenant]
        cls._tenant_stack.set(new_stack)

    @classmethod
    def pop_tenant(cls):
        """Remove the top tenant from the current context's tenant stack.

        This is a no-op when the stack is already empty.
        """

        stack = cls._tenant_stack.get()
        if stack:
            new_stack = stack[:-1]
            cls._tenant_stack.set(new_stack)

    # --- Database ---
    @classmethod
    def get_db_alias(cls):
        """Return the active database alias for the current context.

        Falls back to ``settings.PUBLIC_DB_ALIAS`` if the stack is empty.
        """

        stack = cls._db_alias_stack.get()
        return stack[-1] if stack else settings.PUBLIC_DB_ALIAS

    @classmethod
    def push_db_alias(cls, db_alias):
        """Push a database alias onto the current context's DB alias stack.

        Args:
            db_alias: a string representing the Django database alias.
        """

        stack = cls._db_alias_stack.get()
        new_stack = stack + [db_alias]
        cls._db_alias_stack.set(new_stack)

    @classmethod
    def pop_db_alias(cls):
        """Pop the current database alias from the DB alias stack.

        No-op if the stack is empty.
        """

        stack = cls._db_alias_stack.get()
        if stack:
            new_stack = stack[:-1]
            cls._db_alias_stack.set(new_stack)

    # --- Cache ---
    @classmethod
    def get_cache_alias(cls):
        """Return the active cache alias for the current context.

        Falls back to the Django ``default`` cache when the stack is empty.
        """

        stack = cls._cache_alias_stack.get()
        return stack[-1] if stack else "default"

    @classmethod
    def push_cache_alias(cls, cache_alias):
        """Push a cache alias onto the current context's cache alias stack.

        Args:
            cache_alias: a string representing the cache alias to use.
        """

        stack = cls._cache_alias_stack.get()
        new_stack = stack + [cache_alias]
        cls._cache_alias_stack.set(new_stack)

    @classmethod
    def pop_cache_alias(cls):
        """Pop the current cache alias from the cache alias stack.

        No-op if the stack is empty.
        """

        stack = cls._cache_alias_stack.get()
        if stack:
            new_stack = stack[:-1]
            cls._cache_alias_stack.set(new_stack)

    # --- Clear all (reset to defaults) ---
    @classmethod
    def clear_all(cls):
        """Reset all context stacks to their default values.

        This sets an empty tenant stack and restores the DB/cache alias
        stacks to the public/master defaults defined in settings.
        """

        cls._tenant_stack.set([])
        cls._db_alias_stack.set([settings.PUBLIC_DB_ALIAS])
        cls._cache_alias_stack.set(["default"])

    # --- Context manager ---
    @classmethod
    @contextmanager
    def use_tenant(cls, tenant):
        """Context manager that activates tenant-specific backends.

        This helper performs the following steps:

        1. Pushes ``tenant`` onto the tenant stack.
        2. Activates the appropriate database/schema backend for the tenant
           and pushes the resulting DB alias.
        3. Activates the cache backend for the tenant and pushes the cache
           alias.

        Upon exit the backends are deactivated and the pushed values are
        popped from their respective stacks.

        Args:
            tenant: a :class:`BaseTenant` instance to activate.
        """

        from django_omnitenant.backends.cache_backend import CacheTenantBackend
        from django_omnitenant.backends.database_backend import DatabaseTenantBackend
        from django_omnitenant.backends.schema_backend import SchemaTenantBackend

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
        """Temporarily switch to an existing schema by name.

        This constructs a lightweight mock tenant object for the provided
        ``schema_name``, activates the schema backend and yields control to
        the caller. On exit the backend is deactivated and the DB alias
        is popped.

        Args:
            schema_name: the schema name to switch to (usually a string).
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

    @classmethod
    @contextmanager
    def use_master_db(cls):
        """Context manager that temporarily switches to the master DB.

        This is useful for operations that must run against the primary
        (master) database and its corresponding cache. It pushes the
        master DB/cache aliases, activates the default backends and
        restores the previous state on exit.
        """

        from django_omnitenant.backends.cache_backend import CacheTenantBackend
        from django_omnitenant.backends.database_backend import DatabaseTenantBackend

        # Push default DB & cache
        master_db = settings.MASTER_DB_ALIAS
        master_cache = settings.MASTER_DB_ALIAS

        cls.push_db_alias(master_db)
        cls.push_cache_alias(master_cache)

        # Activate default backends
        tenant: BaseTenant = get_tenant_model()(tenant_id=settings.PUBLIC_TENANT_NAME)
        db_backend = DatabaseTenantBackend(tenant)  # None means no specific tenant
        db_backend.activate()
        cache_backend = CacheTenantBackend(tenant)
        cache_backend.activate()

        try:
            yield
        finally:
            db_backend.deactivate()
            cache_backend.deactivate()
            cls.pop_db_alias()
            cls.pop_cache_alias()

    # --- New: use public schema ---
    @classmethod
    @contextmanager
    def use_public_schema(cls):
        """Activate the public (shared) schema and cache for the context.

        This constructs a mock tenant representing the public schema,
        activates the schema & cache backends and pushes the resulting
        DB/cache aliases. On exit the backends are deactivated and the
        aliases are popped.
        """

        from django_omnitenant.backends.cache_backend import CacheTenantBackend
        from django_omnitenant.backends.schema_backend import SchemaTenantBackend

        # Create a mock tenant representing public schema
        tenant: BaseTenant = get_tenant_model()(tenant_id="public")  # type: ignore
        backend = SchemaTenantBackend(tenant)
        backend.activate()
        cls.push_db_alias(cls.get_db_alias())

        # Public cache
        cache_backend = CacheTenantBackend(tenant)
        cache_backend.activate()
        cls.push_cache_alias(cls.get_cache_alias())

        try:
            yield
        finally:
            backend.deactivate()
            cache_backend.deactivate()
            cls.pop_db_alias()
            cls.pop_cache_alias()
