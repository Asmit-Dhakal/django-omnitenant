from django.core.management.commands.migrate import Command as BaseMigrateCommand
from django.core.management.base import CommandError
from django_omnitenant.models import BaseTenant
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_tenant_model
from django_omnitenant.backends.schema_backend import SchemaTenantBackend
from django_omnitenant.backends.database_backend import DatabaseTenantBackend


class Command(BaseMigrateCommand):
    help = "Custom migrate command for tenants."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "target",
            nargs="?",
            default="shared",
            choices=["tenant", "alltenants", "shared"],
            help="Target for migration: single tenant, all tenants, or shared/public DB",
        )
        parser.add_argument(
            "--tenant-id",
            help="Identifier of the tenant (required if target=tenant)",
        )

    def handle(self, *args, **options):
        target = options["target"]

        if target == "tenant":
            tenant_id = options.get("tenant_id")
            if not tenant_id:
                raise CommandError("You must provide --tenant-id when target=tenant")
            self.migrate_single_tenant(tenant_id, *args, **options)

        elif target == "alltenants":
            self.migrate_all_tenants(*args, **options)

        elif target == "shared":
            super().handle(*args, **options)

    def migrate_single_tenant(self, tenant_id, *args, **options):
        Tenant = get_tenant_model()
        try:
            tenant: BaseTenant = Tenant.objects.get(identifier=tenant_id)  # type: ignore
        except Tenant.DoesNotExist:
            raise CommandError(f"Tenant '{tenant_id}' does not exist")

        TenantContext.set_tenant(tenant)

        backend = (
            SchemaTenantBackend(tenant)
            if tenant.backend_type == BaseTenant.BackendType.SCHEMA
            else DatabaseTenantBackend(tenant)
        )
        backend.activate()
        try:
            super().handle(*args, **options)
        finally:
            backend.deactivate()
            TenantContext.clear_tenant()

    def migrate_all_tenants(self, *args, **options):
        Tenant = get_tenant_model()
        for tenant in Tenant.objects.all():  # type: ignore
            tenant: BaseTenant = tenant
            self.stdout.write(f"Migrating tenant: {tenant.tenant_id}")
            self.migrate_single_tenant(tenant.tenant_id, *args, **options)
