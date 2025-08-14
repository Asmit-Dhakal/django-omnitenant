from django.core.management.base import BaseCommand
from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_model
from django_omnitenant.management.commands.migrate_tenant import (
    Command as MigrateTenantCommand,
)


class Command(BaseCommand):
    help = "Run migrations for all tenants."

    def handle(self, *args, **options):
        Tenant = get_tenant_model()
        migrate_single = MigrateTenantCommand()

        for tenant in Tenant.objects.all():  # type: ignore
            tenant: BaseTenant = tenant
            self.stdout.write(f"Migrating tenant: {tenant.tenant_id}")
            migrate_single.handle(tenant_id=tenant.tenant_id)
