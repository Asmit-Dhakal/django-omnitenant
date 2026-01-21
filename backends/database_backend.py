from django.core.management import call_command
from django.db import connection
from requests.structures import CaseInsensitiveDict

from django_omnitenant.conf import settings
from django_omnitenant.constants import constants
from django_omnitenant.models import BaseTenant
from django_omnitenant.signals import tenant_deleted
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_active_schema_name

from .base import BaseTenantBackend

try:
    from django.db.backends.postgresql.psycopg_any import is_psycopg3
except ImportError:
    is_psycopg3 = False

if is_psycopg3:
    import psycopg as psycopg_driver
else:
    import psycopg2 as psycopg_driver


class DatabaseTenantBackend(BaseTenantBackend):
    def __init__(self, tenant: BaseTenant):
        super().__init__(tenant)
        self.db_config: CaseInsensitiveDict = CaseInsensitiveDict(self.tenant.config.get("db_config", {}))

    def create(self, run_migrations=False, **kwargs):
        _, db_config = self.get_alias_and_config(self.tenant)

        self._create_database(
            db_config["NAME"],
            db_config["USER"],
            db_config["PASSWORD"],
            db_config["HOST"],
            db_config["PORT"],
        )
        super().create(run_migrations=run_migrations)

    def migrate(self, *args, **kwargs):
        db_alias, _ = self.get_alias_and_config(self.tenant)
        with TenantContext.use_tenant(self.tenant):
            try:
                call_command("migrate", *args, database=db_alias, **kwargs)
            except Exception as e:
                print(f"[DB BACKEND] Migration failed for db `{db_alias}`: {e}")
                raise
        super().migrate()

    def delete(self, drop_db=False):
        db_alias, db_config = self.get_alias_and_config(self.tenant)
        if drop_db:
            self._drop_database(
                db_config["NAME"],
                db_config["USER"],
                db_config["PASSWORD"],
                db_config["HOST"],
                db_config["PORT"],
            )
        if db_alias in settings.DATABASES:
            del settings.DATABASES[db_alias]
        super().delete()

    def bind(self):
        db_alias, db_config = self.get_alias_and_config(self.tenant)
        settings.DATABASES[db_alias] = db_config
        print(f"[DB BACKEND] Bound tenant {self.tenant.tenant_id} to alias {db_alias}.")

    def activate(self):
        db_alias = self.db_config.get("ALIAS") or self.db_config.get("NAME") or settings.MASTER_DB_ALIAS
        if db_alias not in settings.DATABASES:
            self.bind()
        TenantContext.push_db_alias(db_alias)

        self.previous_schema = get_active_schema_name(connection)
        connection.set_schema(
            "public"
        )  # If a tenant is using scheman backend then while using use_default_db won't work properly as the db will already be the default one in that case so we need to change the schema to public

    def deactivate(self):
        TenantContext.pop_db_alias()
        connection.set_schema(self.previous_schema)

    # --- helpers ---
    @classmethod
    def get_alias_and_config(cls, tenant):
        """
        Returns the database alias and resolved configuration for the tenant.
        """
        db_config = CaseInsensitiveDict(tenant.config.get("db_config", {}))

        db_alias = db_config.get("ALIAS") or db_config.get("NAME") or settings.MASTER_DB_ALIAS

        base_config: dict = settings.DATABASES.get(settings.MASTER_DB_ALIAS, {}).copy()

        resolved_config = {
            "ENGINE": db_config.get("ENGINE") or base_config.get("ENGINE", "django_omnitenant.backends.postgresql"),
            "NAME": db_config.get("NAME") or base_config.get("NAME"),
            "USER": db_config.get("USER") or base_config.get("USER"),
            "PASSWORD": db_config.get("PASSWORD") or base_config.get("PASSWORD"),
            "HOST": db_config.get("HOST") or base_config.get("HOST"),
            "PORT": db_config.get("PORT") or base_config.get("PORT"),
            "OPTIONS": db_config.get("OPTIONS") or base_config.get("OPTIONS", {}),
            "TIME_ZONE": db_config.get("TIME_ZONE") or base_config.get("TIME_ZONE", settings.TIME_ZONE),
            "ATOMIC_REQUESTS": db_config.get("ATOMIC_REQUESTS")
            if "ATOMIC_REQUESTS" in db_config
            else base_config.get("ATOMIC_REQUESTS", False),
            "AUTOCOMMIT": db_config.get("AUTOCOMMIT")
            if "AUTOCOMMIT" in db_config
            else base_config.get("AUTOCOMMIT", True),
            "CONN_MAX_AGE": db_config.get("CONN_MAX_AGE")
            if "CONN_MAX_AGE" in db_config
            else base_config.get("CONN_MAX_AGE", 0),
            "CONN_HEALTH_CHECKS": db_config.get("CONN_HEALTH_CHECKS")
            if "CONN_HEALTH_CHECKS" in db_config
            else base_config.get("CONN_HEALTH_CHECKS", False),
            "TEST": db_config.get("TEST") if "TEST" in db_config else base_config.get("TEST", {}),
        }
        if not resolved_config["TEST"].get("NAME"):
            resolved_config["TEST"]["NAME"] = resolved_config["NAME"]

        return db_alias, resolved_config

    def _create_database(self, db_name, user, password, host, port):
        conn = psycopg_driver.connect(dbname="postgres", user=user, password=password, host=host, port=port)
        conn.autocommit = True
        cur = conn.cursor()
        try:
            if is_psycopg3:
                from psycopg import sql
            else:
                from psycopg2 import sql

            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            print(f"[DB BACKEND] Database '{db_name}' created.")
        except Exception as e:
            print(f"[DB BACKEND] Skipped DB create: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    def _drop_database(self, db_name, user, password, host, port):
        conn = psycopg2.connect(dbname="postgres", user=user, password=password, host=host, port=port)
        conn.autocommit = True
        cur = conn.cursor()
        try:
            cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
            print(f"[DB BACKEND] Database '{db_name}' dropped.")
        finally:
            cur.close()
            conn.close()
