from django.db.backends.postgresql.base import (
    DatabaseWrapper as PostgresDatabaseWrapper,
)

from django_omnitenant.conf import settings


class DatabaseWrapper(PostgresDatabaseWrapper):
    """
    PostgreSQL wrapper that supports switching schemas per tenant
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_schema = settings.DEFAULT_TENANT_NAME
        # self._current_schema = "public"

    def set_schema(self, schema_name):
        """
        Switch the PostgreSQL schema for this connection.
        """
        if not self.is_usable():
            self.ensure_connection()

        with self.cursor() as cursor:
            cursor.execute(f'SET search_path TO "{schema_name}"')

        self._current_schema = schema_name

    def set_schema_to_public(self):
        """
        Reset to the public schema.
        """
        self.set_schema(settings.DEFAULT_TENANT_NAME)
        # self.set_schema("public")

    @property
    def current_schema(self):
        return self._current_schema
