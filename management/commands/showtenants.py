from django.core.management.base import BaseCommand
from django_omnitenant.utils import get_tenant_model
from django_omnitenant.models import BaseTenant


class Command(BaseCommand):
    help = "List all tenants with their details"

    def add_arguments(self, parser):
        parser.add_argument(
            "--isolation-type",
            type=str,
            help="Filter by isolation type (database/schema/table)",
        )
        parser.add_argument(
            "--format",
            type=str,
            choices=["table", "json", "csv"],
            default="table",
            help="Output format (default: table)",
        )

    def handle(self, *args, **options):
        TenantModel = get_tenant_model()
        tenants = TenantModel.objects.all()

        # Apply filters
        isolation_type = options.get("isolation_type")
        if isolation_type:
            isolation_type_upper = isolation_type.upper()
            valid_types = {choice[0] for choice in BaseTenant.IsolationType.choices}
            if isolation_type_upper in valid_types:
                tenants = tenants.filter(isolation_type=isolation_type_upper)
            else:
                self.stdout.write(self.style.ERROR(f"Invalid isolation type. Valid options: {', '.join(valid_types)}"))
                return

        if not tenants.exists():
            self.stdout.write(self.style.WARNING("No tenants found."))
            return

        output_format = options.get("format")

        if output_format == "json":
            self._output_json(tenants)
        elif output_format == "csv":
            self._output_csv(tenants)
        else:
            self._output_table(tenants)

    def _output_table(self, tenants):
        """Display tenants in a formatted table"""
        self.stdout.write(self.style.SUCCESS(f"\nFound {tenants.count()} tenant(s):\n"))

        # Header
        header = f"{'Tenant ID':<20} {'Name':<30} {'Isolation':<15} {'Domain':<30} {'Created':<20}"
        self.stdout.write(self.style.SUCCESS(header))
        self.stdout.write(self.style.SUCCESS("-" * len(header)))

        # Rows
        for tenant in tenants:
            created = tenant.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(tenant, "created_at") else "N/A"
            isolation_display = (
                tenant.get_isolation_type_display()
                if hasattr(tenant, "get_isolation_type_display")
                else tenant.isolation_type
            )

            row = f"{tenant.tenant_id:<20} {tenant.name:<30} {isolation_display:<15} {tenant.domain.domain:<30} {created:<20}"
            self.stdout.write(row)

            # Show DB config if exists
            if tenant.config and tenant.config.get("db_config"):
                db_config = tenant.config["db_config"]
                if db_config.get("NAME"):
                    self.stdout.write(
                        self.style.WARNING(
                            f"           └─ Database: {db_config.get('NAME')} @ {db_config.get('HOST')}:{db_config.get('PORT')}"
                        )
                    )
            self.stdout.write("")

    def _output_json(self, tenants):
        """Display tenants in JSON format"""
        import json

        tenant_list = []
        for tenant in tenants:
            tenant_data = {
                "id": tenant.id,
                "tenant_id": tenant.tenant_id,
                "name": tenant.name,
                "isolation_type": tenant.isolation_type,
                "config": tenant.config,
            }
            if hasattr(tenant, "created_at"):
                tenant_data["created_at"] = tenant.created_at.isoformat()
            if hasattr(tenant, "updated_at"):
                tenant_data["updated_at"] = tenant.updated_at.isoformat()

            tenant_list.append(tenant_data)

        self.stdout.write(json.dumps(tenant_list, indent=2))

    def _output_csv(self, tenants):
        """Display tenants in CSV format"""
        import csv
        import sys

        writer = csv.writer(sys.stdout)

        # Header
        writer.writerow(["ID", "Tenant ID", "Name", "Isolation Type", "Created At", "DB Name", "DB Host"])

        # Rows
        for tenant in tenants:
            created = tenant.created_at.isoformat() if hasattr(tenant, "created_at") else ""
            db_name = ""
            db_host = ""

            if tenant.config and tenant.config.get("db_config"):
                db_config = tenant.config["db_config"]
                db_name = db_config.get("NAME", "")
                db_host = db_config.get("HOST", "")

            writer.writerow(
                [tenant.id, tenant.tenant_id, tenant.name, tenant.isolation_type, created, db_name, db_host]
            )
