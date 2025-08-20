from django.core.management.commands.shell import Command as ShellCommand

from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_tenant_model


class Command(ShellCommand):
    help = "Runs a Django shell with a specific tenant activated."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--tenant-id", type=str, help="Tenant ID to activate")

    def handle(self, *args, **options):
        tenant_id = options.get("tenant_id")
        if tenant_id:
            Tenant = get_tenant_model()
            try:
                tenant = Tenant.objects.get(tenant_id=tenant_id)
            except Tenant.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f"Tenant with ID '{tenant_id}' does not exist.")
                )
                return
            with TenantContext.use_tenant(tenant):
                self.stdout.write(
                    self.style.SUCCESS(f"Tenant '{tenant_id}' activated.")
                )
                super().handle(*args, **options)
        else:
            super().handle(*args, **options)
