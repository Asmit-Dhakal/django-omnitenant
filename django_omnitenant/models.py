"""Base tenant and domain models for django_omnitenant.

This module defines lightweight, reusable abstract model bases intended
for use in multi-tenant Django projects. It focuses on two primary
concepts:

- ``BaseTenant``: An abstract representation of a tenant (a tenant may
    be isolated by schema or by database). The model contains identifying
    fields and a ``config`` JSON field used to store backend-specific
    connection/configuration information. When a tenant's isolation or
    config changes the model coordinates updating the project's
    ``settings.DATABASES`` and ``settings.CACHES`` and resets active
    connections so runtime code can pick up the new configuration.

- ``BaseDomain``: A simple mapping between a tenant and a DNS-style
    domain name, intended for projects that resolve tenants by domain or
    host header.

Utilities
---------
The module also provides ``TenantQuerySetManager`` which is a manager
used by tenant-scoped models to prevent accidental access to models
that are not available to the current tenant. It uses
``get_current_tenant`` (from :mod:`.utils`) and inspects model-level
attributes such as ``master_managed`` and ``tenant_managed`` to
determine whether the current tenant should be allowed to access the
model.

Notes on integration
--------------------
- Both model classes are ``abstract``; concrete projects should subclass
    them and include any project-specific fields.
- The save/delete hooks in ``BaseTenant`` import and interact with the
    backend modules at runtime. This keeps the core model free of direct
    backend imports until they are required, reducing startup cost and
    avoiding circular import issues.
"""

from django.db import models

from .conf import settings
from .utils import get_current_tenant, get_tenant_backend
from .validators import validate_dns_label, validate_domain_name


class TenantQuerySetManager(models.Manager):
    """Manager enforcing tenant-aware access controls for querysets.

    Use this manager for models that should be protected from access by
    non-authorized tenants (for example models that are shared globally
    or reserved for a single master tenant). The manager consults the
    current tenant (via :func:`get_current_tenant`) and the model's
    attributes ``master_managed`` and ``tenant_managed`` to decide
    whether access should be permitted.

    Behavior
    --------
    - If no current tenant is present (for example during certain
      background tasks) no access check is performed.
    - By default a model is considered tenant-managed (``tenant_managed=True``).
      If a model sets ``tenant_managed=False`` it is considered shared
      and access is restricted to the public/master tenant unless
      ``master_managed=True`` is explicitly set on the model or the app.
    """

    def _check_tenant_access(self) -> None:
        """Internal helper that raises ``PermissionError`` when the
        currently active tenant must not access this model.

        The check is intentionally conservative: when a model is
        explicitly configured as not tenant-managed we only allow access
        when the active tenant is the public/master tenant.
        """

        tenant = get_current_tenant()
        if not tenant:
            return

        # By default, models are tenant-managed unless explicitly marked
        if not getattr(self.model, "master_managed", False) and not getattr(
            self.model, "tenant_managed", True
        ):
            if tenant.tenant_id != settings.PUBLIC_TENANT_NAME:
                raise PermissionError(
                    f"Model '{self.model.__name__}' is not accessible from '{tenant.name}'"
                )

    def get_queryset(self):
        """Return the base queryset after performing tenant access checks.

        Concrete models should use this manager instead of the default
        manager if they need automatic tenant access enforcement for all
        queryset operations.
        """

        self._check_tenant_access()
        return super().get_queryset()


class BaseTenant(models.Model):
    """Abstract tenant model providing identity and lifecycle hooks.

    Subclass this model to add tenant records to a concrete project. The
    class captures three important pieces of information:

    - ``name``: human readable tenant name
    - ``tenant_id``: a slug/identifier used for routing and aliasing. And also for the schema name if `isolation` type is `schema`
    - ``isolation_type``: whether the tenant is isolated by schema or by
      a separate database

    The ``config`` JSONField is intended to store backend-specific
    settings such as connection strings or per-tenant options. When
    fields that affect the runtime connection configuration (for
    example ``config`` or ``isolation_type``) change, the model's
    ``save`` hook updates ``settings.DATABASES``/``settings.CACHES`` and
    resets the relevant Django connections so the application can begin
    using the new configuration without a full restart.
    """

    class IsolationType(models.IntegerChoices):
        """Enumeration for tenant isolation strategies.

        - ``SCHEMA``: tenant lives in a separate database schema
        - ``DATABASE``: tenant lives in its own database (different alias)
        """

        SCHEMA = 0, "Schema"
        DATABASE = 1, "Database"
        # HYBRID = "HYB", "Hybrid"

    name = models.CharField(max_length=100)
    tenant_id = models.SlugField(
        unique=True,
        validators=[validate_dns_label],
        help_text="Must be a valid DNS label (RFC 1034/1035).",
    )
    isolation_type = models.PositiveSmallIntegerField(choices=IsolationType.choices)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Backend-specific configuration or metadata, such as connection strings.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Use the tenant-aware manager so queries are subject to tenant access checks
    objects: TenantQuerySetManager = TenantQuerySetManager()

    class Meta:
        abstract = True

    def __str__(self):
        """Return a compact, human-readable representation of the tenant."""

        return f"{self.name}({self.tenant_id})"

    def save(self, *args, **kwargs):
        """Persist the tenant and apply any runtime configuration updates.

        The method performs the following steps:

        1. Detects which fields changed compared to the stored instance
           (when updating an existing record).
        2. Saves the model using the standard Django flow.
        3. If ``config`` or ``isolation_type`` were changed, update
           ``settings.DATABASES`` and/or ``settings.CACHES`` and reset
           DB/cache connections so the running process can pick up the
           new backend configuration.

        Note: backend imports are performed lazily inside the method to
        avoid circular imports and to keep module import time small.
        """

        if self.pk:
            old = type(self).objects.get(pk=self.pk)
            changed_fields = [
                f.name
                for f in self._meta.fields
                if getattr(old, f.name) != getattr(self, f.name)
            ]
        else:
            changed_fields = []

        super().save(*args, **kwargs)

        if any(field in changed_fields for field in ["config", "isolation_type"]):
            from django_omnitenant.backends.cache_backend import CacheTenantBackend

            from .utils import reset_cache_connection, reset_db_connection

            if self.isolation_type == self.IsolationType.DATABASE:
                from django_omnitenant.backends.database_backend import (
                    DatabaseTenantBackend,
                )

                alias, config = DatabaseTenantBackend.get_alias_and_config(self)
                settings.DATABASES[alias] = config
                reset_db_connection(alias)

            alias, config = CacheTenantBackend.get_alias_and_config(self)
            settings.CACHES[alias] = config
            reset_cache_connection(alias)

    def delete(self, *args, **kwargs):
        """Delete the tenant and instruct the configured backend to remove resources.

        After the database record is removed the tenant backend is asked to
        perform any required cleanup (for example dropping a schema or
        removing an external database). The method returns the result of
        ``super().delete()``.
        """

        result = super().delete(*args, **kwargs)
        backend = get_tenant_backend(self)
        backend.delete()
        return result


class BaseDomain(models.Model):
    """Abstract model mapping a tenant to a DNS-style domain name.

    Subclass this model to provide tenant-to-domain mappings used by
    resolvers that identify tenants from host headers. The model stores
    a one-to-one relation to the configured tenant model and a unique
    domain string which must be a valid DNS name.
    """

    tenant = models.OneToOneField(
        settings.TENANT_MODEL,
        on_delete=models.CASCADE,
        help_text="The tenant this domain belongs to.",
    )
    domain = models.CharField(
        unique=True,
        validators=[validate_domain_name],
        help_text="Must be a valid DNS label (RFC 1034/1035).",
    )

    objects: TenantQuerySetManager = TenantQuerySetManager()

    def __str__(self):
        """Return a compact representation showing tenant and domain."""

        return f"{str(self.tenant)} => {self.domain}"

    class Meta:
        abstract = True
        unique_together = ("tenant", "domain")
