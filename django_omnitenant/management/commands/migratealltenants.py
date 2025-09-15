from django.core.management.base import BaseCommand
from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_model
from django_omnitenant.utils import get_tenant_backend


class Command(BaseCommand):
    help = "Run migrations for all tenants."

    def handle(self, *args, **options):
        Tenant = get_tenant_model()

        for tenant in Tenant.objects.all():  # type: ignore
            tenant: BaseTenant = tenant
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"Migrating tenant: {tenant.tenant_id}")
            )

            try:
                backend = get_tenant_backend(tenant)
                backend.migrate()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Tenant '{tenant.tenant_id}' migrated successfully."
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Migrations failed for tenant '{tenant.tenant_id}': {e}"
                    )
                )
