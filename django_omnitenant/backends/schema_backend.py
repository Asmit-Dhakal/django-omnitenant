from django.db import connection

from django_omnitenant.models import BaseTenant
from .base import BaseTenantBackend
from django_omnitenant.utils import get_active_schema_name


class SchemaTenantBackend(BaseTenantBackend):
    def __init__(self, tenant: BaseTenant):
        super().__init__(tenant)
        self.schema_name = tenant.config.get("schema_name") or tenant.tenant_id

    def bind(self):
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema_name}"')

        # can run  migrations for this schema here
        print(f"Schema {self.schema_name} created.")

    def activate(self):
        self.bind()
        self.pervious_schema = get_active_schema_name(connection)
        connection.set_schema(self.schema_name)

    def deactivate(self):
        # connection.set_schema_to_public()
        connection.set_schema(self.pervious_schema)
