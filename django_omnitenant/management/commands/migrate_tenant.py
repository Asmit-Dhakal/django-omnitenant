from django.core.management.base import BaseCommand, CommandError
from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_model
from django_omnitenant.utils import get_tenant_backend


class Command(BaseCommand):
    help = "Run migrations for a single tenant."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id",
            help="Identifier of the tenant to migrate. "
            "Required when running this command directly.",
        )

    def handle(self, *args, **options):
        tenant_id = options.pop("tenant_id", None)
        Tenant = get_tenant_model()

        if not tenant_id:
            raise CommandError(
                "--tenant-id is required when running migrate_tenant directly."
            )

        try:
            tenant: BaseTenant = Tenant.objects.get(tenant_id=tenant_id)  # type: ignore
        except Tenant.DoesNotExist:
            raise CommandError(
                f"Tenant '{tenant_id}' does not exist. "
                f"Please create one with the tenant id '{tenant_id}' first."
            )

        self.stdout.write(
            self.style.SUCCESS(f"Running migrations for tenant: {tenant}")
        )

        try:
            backend = get_tenant_backend(tenant)
            backend.migrate(*args, **options)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Migrations completed successfully for tenant '{tenant_id}'."
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Migrations failed for tenant '{tenant_id}': {e}")
            )
