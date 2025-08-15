from django.db import models
from .validators import validate_dns_label


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
