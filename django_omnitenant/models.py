from django.db import models

from .conf import settings
from .utils import get_current_tenant, get_tenant_backend
from .validators import validate_dns_label, validate_domain_name


class TenantQuerySetManager(models.Manager):
    """Tenant-aware manager with common queryset helpers."""

    def _check_tenant_access(self) -> None:
        """Raise if the current tenant is not allowed to access this model."""
        tenant = get_current_tenant()
        if not tenant:
            return

        # By default, models are tenant-managed unless explicitly marked
        if not getattr(self.model, "globally_managed", False) and not getattr(
            self.model, "tenant_managed", True
        ):
            if tenant.tenant_id != settings.DEFAULT_TENANT_NAME:
                raise PermissionError(
                    f"Model '{self.model.__name__}' is not accessible "
                    f"from '{tenant.name}'"
                )

    def get_queryset(self):
        self._check_tenant_access()
        return super().get_queryset()


class BaseTenant(models.Model):
    class IsolationType(models.TextChoices):
        SCHEMA = "SCH", "Schema"
        DATABASE = "DB", "Database"
        # HYBRID = "HYB", "Hybrid"

    name = models.CharField(max_length=100)
    tenant_id = models.SlugField(
        unique=True,
        validators=[validate_dns_label],
        help_text="Must be a valid DNS label (RFC 1034/1035).",
    )
    isolation_type = models.CharField(max_length=3, choices=IsolationType.choices)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Backend-specific configuration or metadata, such as connection strings.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects: TenantQuerySetManager = TenantQuerySetManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
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
        result = super().delete(*args, **kwargs)
        backend = get_tenant_backend(self)
        backend.delete()
        return result


class BaseDomain(models.Model):
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

    class Meta:
        abstract = True
        unique_together = ("tenant", "domain")
