from django.core.management.base import BaseCommand
from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_model
from django_omnitenant.management.commands.migrate_tenant import (
    Command as MigrateTenantCommand,
)


class Command(BaseCommand):
    help = "Run migrations for all tenants."

    def __init__(self):
        super().__init__()
        self.migrate_single = MigrateTenantCommand()

    def add_arguments(self, parser):
        self.migrate_single.add_arguments(parser)

    def handle(self, *args, **options):
        Tenant = get_tenant_model()

        # Remove tenant_id from options that might have been passed
        options.pop("tenant_id", None)

        for tenant in Tenant.objects.all():  # type: ignore
            tenant: BaseTenant = tenant
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"Migrating tenant: {tenant.tenant_id}")
            )
            self.migrate_single.handle(*args, tenant_id=tenant.tenant_id, **options)
