from django.contrib.auth.management.commands.createsuperuser import (
    Command as CreateSuperuserCommand,
)
from django.core.management.base import CommandError

from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_tenant_model


class Command(CreateSuperuserCommand):
    help = "Tenant-aware createsuperuser (extends Django’s default command)"

    def add_arguments(self, parser):
        super().add_arguments(parser)  # keep Django’s arguments
        parser.add_argument(
            "--tenant-id",
            required=False,
            help="The tenant_id of the tenant where the superuser should be created. "
            "If not provided, superuser is created in the global context.",
        )

    def handle(self, *args, **options):
        tenant_id = options.pop("tenant_id", None)

        if tenant_id:
            Tenant = get_tenant_model()
            try:
                tenant = Tenant.objects.get(tenant_id=tenant_id)
            except Tenant.DoesNotExist:
                raise CommandError(f"Tenant with id '{tenant_id}' does not exist")

            self.stdout.write(self.style.SUCCESS(f"Using tenant: {tenant.name}"))

            with TenantContext.use_tenant(tenant):
                super().handle(*args, **options)
        else:
            super().handle(*args, **options)
