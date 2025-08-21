from django.db import connection

from django_omnitenant.models import BaseTenant
from .base import BaseTenantBackend
from django_omnitenant.utils import get_active_schema_name

from django.core.management import call_command
from django_omnitenant.tenant_context import TenantContext


class SchemaTenantBackend(BaseTenantBackend):
    def __init__(self, tenant: BaseTenant):
        super().__init__(tenant)
        self.schema_name = tenant.config.get("schema_name") or tenant.tenant_id

    def bind(self):
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema_name}"')
        print(f"[SCHEMA BACKEND] Schema '{self.schema_name}' ensured.")

    def create(self, run_migrations=False, **kwargs):
        self.bind()
        super().create(run_migrations=run_migrations, **kwargs)

    def migrate(self, *args, **kwargs):
        with TenantContext.use_tenant(self.tenant):
            call_command("migrate", *args, database="default", **kwargs)
        super().migrate()

    def delete(self, drop_schema=True):
        if drop_schema:
            with connection.cursor() as cursor:
                cursor.execute(f'DROP SCHEMA IF EXISTS "{self.schema_name}" CASCADE')
            print(f"[SCHEMA BACKEND] Schema '{self.schema_name}' dropped.")
            super().delete()

    def activate(self):
        self.bind()
        self.previous_schema = get_active_schema_name(connection)
        connection.set_schema(self.schema_name)
        super().activate()

    def deactivate(self):
        connection.set_schema(self.previous_schema)
        super().deactivate()
