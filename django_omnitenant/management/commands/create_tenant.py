from django.core.management.base import BaseCommand
from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_model
from django.core.management import call_command

try:
    from django.db.backends.postgresql.psycopg_any import is_psycopg3
except ImportError:
    is_psycopg3 = False

if is_psycopg3:
    import psycopg as psycopg_driver
else:
    import psycopg2 as psycopg_driver


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

        # Ask if migrations should be run immediately
        run_migrations = self._ask_yes_no(
            "Do you want to run migrations for this tenant now?"
        )

        # Ask for DB config if database
        db_config = {}
        create_db = False
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
        tenant = None
        try:
            tenant = get_tenant_model().objects.create(
                tenant_id=tenant_id,
                name=tenant_name,
                isolation_type=isolation_type,
                config={"db_config": db_config},
            )  # type: ignore
            self.stdout.write(
                self.style.SUCCESS(f"Tenant '{tenant_name}' created successfully!")
            )

            # Optionally create the DB
            if create_db:
                self._create_database(
                    db_config["NAME"],
                    db_config["USER"],
                    db_config["PASSWORD"],
                    db_config["HOST"],
                    db_config["PORT"],
                )

            # Run migrations if specified
            if run_migrations:
                self._run_migrations_for_tenant(tenant_id)
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

    def _create_database(self, db_name, db_user, db_password, db_host, db_port):
        """Create the tenant database if not exists (Postgres example)."""

        self.stdout.write(f"Creating database '{db_name}'...")
        conn = psycopg_driver.connect(
            dbname="postgres",
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
        )
        conn.autocommit = True
        cur = conn.cursor()
        try:
            if is_psycopg3:
                from psycopg import sql
            else:
                from psycopg2 import sql
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            self.stdout.write(
                self.style.SUCCESS(f"Database '{db_name}' created successfully.")
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Database creation skipped: {e}"))
        finally:
            cur.close()
            conn.close()

    def _run_migrations_for_tenant(self, tenant_id):
        """Run migrations for the newly created tenant using custom migrate_tenant command."""
        try:
            call_command("migrate_tenant", tenant_id=tenant_id)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Migrations completed successfully for tenant '{tenant_id}'."
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Migrations failed for tenant '{tenant_id}': {e}")
            )

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
