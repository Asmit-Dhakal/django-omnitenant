from django.db import models


class BaseTenant(models.Model):
    class BackendType(models.TextChoices):
        SCHEMA = "SCH", "Schema"
        DATABASE = "DB", "Database"
        # HYBRID = "HYB", "Hybrid"

    name = models.CharField(max_length=100)
    tenant_id = models.SlugField(unique=True)
    backend_type = models.CharField(max_length=3, choices=BackendType.choices)
    config = models.JSONField(default=dict, blank=True)  # backend-specific details
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
