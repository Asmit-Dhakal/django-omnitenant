from .base import BaseTenantBackend
from django_omnitenant.conf import settings
from django_omnitenant.constants import constants
from django_omnitenant.tenant_context import TenantContext
from requests.structures import CaseInsensitiveDict


class DatabaseTenantBackend(BaseTenantBackend):
    def __init__(self, tenant):
        super().__init__(tenant)
        self.db_config: CaseInsensitiveDict = CaseInsensitiveDict(
            self.tenant.config.get("db_config", {})
        )

    def bind(self):
        db_alias = self.db_config.get("ALIAS") or self.db_config.get("NAME")
        base_config: dict = settings.DATABASES.get(
            constants.DEFAULT_DB_ALIAS, {}
        ).copy()

        settings.DATABASES[db_alias] = {
            "ENGINE": self.db_config.get("ENGINE")
            or base_config.get("ENGINE", "django.db.backends.postgresql"),
            "NAME": self.db_config.get("NAME") or base_config.get("NAME"),
            "USER": self.db_config.get("USER") or base_config.get("USER"),
            "PASSWORD": self.db_config.get("PASSWORD") or base_config.get("PASSWORD"),
            "HOST": self.db_config.get("HOST") or base_config.get("HOST"),
            "PORT": self.db_config.get("PORT") or base_config.get("PORT"),
            "OPTIONS": self.db_config.get("OPTIONS") or base_config.get("OPTIONS", {}),
            "TIME_ZONE": self.db_config.get("TIME_ZONE")
            or base_config.get("TIME_ZONE", settings.TIME_ZONE),
            "ATOMIC_REQUESTS": self.db_config.get("ATOMIC_REQUESTS")
            if "ATOMIC_REQUESTS" in self.db_config
            else base_config.get("ATOMIC_REQUESTS", False),
            "AUTOCOMMIT": self.db_config.get("AUTOCOMMIT")
            if "AUTOCOMMIT" in self.db_config
            else base_config.get("AUTOCOMMIT", True),
            "CONN_MAX_AGE": self.db_config.get("CONN_MAX_AGE")
            if "CONN_MAX_AGE" in self.db_config
            else base_config.get("CONN_MAX_AGE", 0),
            "CONN_HEALTH_CHECKS": self.db_config.get("CONN_HEALTH_CHECKS")
            if "CONN_HEALTH_CHECKS" in self.db_config
            else base_config.get("CONN_HEALTH_CHECKS", False),
        }

        # Can also create the database externally
        print(f"Database with alias {db_alias} added to settings.DATABASES.")

    def activate(self):
        db_alias = self.db_config.get("ALIAS") or self.db_config.get("NAME")
        if db_alias not in settings.DATABASES:
            self.bind()
        TenantContext.set_db_alias(db_alias)

    def deactivate(self):
        TenantContext.clear_db_alias()
