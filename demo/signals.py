from django.dispatch import receiver
from django_omnitenant.signals import (
    tenant_created,
    tenant_migrated,
    tenant_deleted,
    tenant_activated,
    tenant_deactivated,
)
from demo.models import Hospital


@receiver(tenant_created, sender=Hospital)
def created_signal(sender, **kwargs):
    print("created signal")


@receiver(tenant_migrated, sender=Hospital)
def migrated_signal(sender, **kwargs):
    print("migrated signal")


@receiver(tenant_deleted, sender=Hospital)
def deleted_signal(sender, **kwargs):
    print("deleted signal")


@receiver(tenant_activated, sender=Hospital)
def activated_signal(sender, **kwargs):
    print("activated signal")


@receiver(tenant_deactivated, sender=Hospital)
def deactivated_signal(sender, **kwargs):
    print("deactivated signal")
