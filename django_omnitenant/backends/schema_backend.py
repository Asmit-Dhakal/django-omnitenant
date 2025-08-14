from django.db import connection
from .base import BaseTenantBackend
class SchemaTenantBackend(BaseTenantBackend):
    def __init__(self, tenant):
        super().__init__(tenant)
        self.schema_name = tenant.config.get('schema_name') or tenant.tenant_id

    def bind(self):
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema_name}"')
        
        # can run  migrations for this schema here
        print(f"Schema {self.schema_name} created.")

    def activate(self):
        self.bind()
        connection.set_schema(self.schema_name)

    def deactivate(self):
        connection.set_schema_to_public()
