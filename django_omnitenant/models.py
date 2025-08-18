from django.db import models
from .validators import validate_dns_label
from .conf import settings
from .utils import reset_db_connection, reset_cache_connection


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

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.get(pk=self.pk)
            changed_fields = [
                f.name for f in self._meta.fields
                if getattr(old, f.name) != getattr(self, f.name)
            ]
        else:
            changed_fields = []

        super().save(*args, **kwargs)

        if any(field in changed_fields for field in ["config", "isolation_type"]):
            if self.isolation_type == self.IsolationType.DATABASE:
                from django_omnitenant.backends.database_backend import DatabaseTenantBackend
                alias, config = DatabaseTenantBackend.get_alias_and_config(self)
                settings.DATABASES[alias] = config
                reset_db_connection(alias)

            from django_omnitenant.backends.cache_backend import CacheTenantBackend
            alias, config = CacheTenantBackend.get_alias_and_config(self)
            settings.CACHES[alias] = config
            reset_cache_connection(alias)

            




class BaseDomain(models.Model):
    tenant = models.OneToOneField(
        settings.TENANT_MODEL,
        on_delete=models.CASCADE,
        help_text="The tenant this domain belongs to.",
    )
    domain = models.SlugField(
        unique=True,
        validators=[validate_dns_label],
        help_text="Must be a valid DNS label (RFC 1034/1035).",
    )

    class Meta:
        abstract = True
        unique_together = ("tenant", "domain")
