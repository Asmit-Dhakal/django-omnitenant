from .base import BaseTenantBackend
from django_omnitenant.conf import settings
from django_omnitenant.constants import constants
from django_omnitenant.tenant_context import TenantContext


class DatabaseTenantBackend(BaseTenantBackend):
    def bind(self):
        config: dict = self.tenant.config
        db_alias = config.get("db_alias") or config.get("db_name")
        base_config: dict = settings.DATABASES.get(constants.DEFAULT_DB_ALIAS, {}).copy()

        settings.DATABASES[db_alias] = {
            "ENGINE": config.get("db_engine")
            or base_config.get("ENGINE", "django.db.backends.postgresql"),
            "NAME": config.get("db_name") or base_config.get("NAME"),
            "USER": config.get("db_user") or base_config.get("USER"),
            "PASSWORD": config.get("password") or base_config.get("PASSWORD"),
            "HOST": config.get("db_host") or base_config.get("HOST"),
            "PORT": config.get("db_port") or base_config.get("PORT"),
            "OPTIONS": config.get("db_options") or base_config.get("OPTIONS", {}),
            "TIME_ZONE": config.get("time_zone")
            or base_config.get("TIME_ZONE", settings.TIME_ZONE),
            "ATOMIC_REQUESTS": config.get("atomic_requests")
            if "atomic_requests" in config
            else base_config.get("ATOMIC_REQUESTS", False),
            "AUTOCOMMIT": config.get("autocommit")
            if "autocommit" in config
            else base_config.get("AUTOCOMMIT", True),
            "CONN_MAX_AGE": config.get("conn_max_age")
            if "conn_max_age" in config
            else base_config.get("CONN_MAX_AGE", 0),
            "CONN_HEALTH_CHECKS": config.get("conn_health_checks")
            if "conn_health_checks" in config
            else base_config.get("CONN_HEALTH_CHECKS", False),
        }

        # Can also create the database externally
        print(f"Database {db_alias} added to settings.DATABASES.")

    def activate(self):
        db_alias = self.tenant.config.get("db_alias") or self.tenant.config.get("db_name")
        if db_alias not in settings.DATABASES:
            self.bind()
        TenantContext.set_db_alias(db_alias)

    def deactivate(self):
        TenantContext.clear_db_alias()
