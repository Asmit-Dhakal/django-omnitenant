from django.core.management.base import BaseCommand
from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_model, get_tenant_backend


class Command(BaseCommand):
    help = "Create a new tenant interactively"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting tenant creation..."))

        tenant_id = input("Enter tenant ID (unique): ").strip()

        tenant_name = input("Enter tenant name: ").strip()

        valid_inputs = {
            label.lower(): value for value, label in BaseTenant.IsolationType.choices
        }
        isolation_type_input = None
        while isolation_type_input not in valid_inputs:
            isolation_type_input = (
                input(f"Select isolation type ({'/'.join(valid_inputs.keys())}): ")
                .strip()
                .lower()
            )

        isolation_type = valid_inputs[isolation_type_input]

        # Ask for DB config if database
        db_config = {}
        create_db = False

        # Ask if migrations should be run immediately
        run_migrations = self._ask_yes_no(
            "Do you want to run migrations for this tenant now?"
        )
        if isolation_type in (BaseTenant.IsolationType.DATABASE,):
            create_db = self._ask_yes_no(
                "Do you want to create the database now? (y/n): "
            )

            db_name = input("Enter database name for tenant: ").strip()
            db_user = input("Enter database user: ").strip()
            db_password = input("Enter database password: ").strip()
            db_host = input("Enter database host: ").strip()
            db_port = input("Enter database port (default: 5432): ").strip() or "5432"

            db_config = {
                "NAME": db_name,
                "USER": db_user,
                "PASSWORD": db_password,
                "HOST": db_host,
                "PORT": db_port,
            }

        # Create tenant
        tenant = None  # type: ignore
        tenant: BaseTenant = get_tenant_model().objects.create(
            tenant_id=tenant_id,
            name=tenant_name,
            isolation_type=isolation_type,
            config={"db_config": db_config},
        )  # type: ignore
        self.stdout.write(
            self.style.SUCCESS(f"Tenant '{tenant_name}' created successfully!")
        )
        backend = get_tenant_backend(tenant)

        try:
            if tenant.isolation_type == BaseTenant.IsolationType.DATABASE:
                if create_db:
                    self.stdout.write(f"Creating database '{db_name}'...")
                    backend.create(run_migrations=run_migrations)
                elif run_migrations:
                    backend.migrate()

            elif tenant.isolation_type == BaseTenant.IsolationType.SCHEMA:
                backend.create(run_migrations=run_migrations)
        except Exception as e:
            # If DB already exists, continue; else rollback tenant
            if "already exists" in str(e).lower():
                self.stdout.write(
                    self.style.WARNING(
                        "DB already exists. Tenant creation continues..."
                    )
                )
            else:
                if tenant:
                    tenant.delete()
                self.stdout.write(self.style.ERROR(f"Tenant creation failed: {e}"))
                return

        self.stdout.write(self.style.SUCCESS("Tenant setup complete."))

    def _ask_yes_no(self, prompt: str) -> bool:
        """Ask the user a yes/no question until a valid response is given."""
        valid_yes = {"y", "yes"}
        valid_no = {"n", "no"}
        while True:
            answer = input(f"{prompt} (y/n): ").strip().lower()
            if answer in valid_yes:
                return True
            elif answer in valid_no:
                return False
            else:
                self.stdout.write(
                    self.style.ERROR("Please enter 'y' or 'n' (or 'yes' / 'no').")
                )
