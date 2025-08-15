from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_model
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.backends import SchemaTenantBackend,DatabaseTenantBackend

# TODO: Add support for --fake and --database

class Command(BaseCommand):
    help = "Run migrations for a single tenant."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id",
            required=True,
            help="Identifier of the tenant to migrate",
        )

    def handle(self, *args, **options):
        tenant_id = options["tenant_id"]
        Tenant = get_tenant_model()

        try:
            tenant: BaseTenant = Tenant.objects.get(tenant_id=tenant_id) # type: ignore
        except Tenant.DoesNotExist:
            raise CommandError(f"Tenant '{tenant_id}' does not exist. Please create one with the tenant id '{tenant_id}' first.")

        TenantContext.set_tenant(tenant)
        backend = (
            SchemaTenantBackend(tenant)
            if tenant.isolation_type == BaseTenant.IsolationType.SCHEMA
            else DatabaseTenantBackend(tenant)
        )
        backend.activate()
        try:
            self.stdout.write(self.style.SUCCESS(f"Running migrations for tenant: {tenant}"))
            db_alias: str = TenantContext.get_db_alias()
            call_command("migrate", database=db_alias)
        finally:
            backend.deactivate()
            TenantContext.clear_tenant()
