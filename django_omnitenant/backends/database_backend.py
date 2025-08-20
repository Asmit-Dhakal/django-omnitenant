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

    @classmethod
    def get_alias_and_config(cls, tenant):
        """
        Returns the database alias and resolved configuration for the tenant.
        """
        db_config = CaseInsensitiveDict(tenant.config.get("db_config", {}))

        db_alias = (
            db_config.get("ALIAS")
            or db_config.get("NAME")
            or constants.DEFAULT_DB_ALIAS
        )

        base_config: dict = settings.DATABASES.get(
            constants.DEFAULT_DB_ALIAS, {}
        ).copy()

        resolved_config = {
            "ENGINE": db_config.get("ENGINE")
            or base_config.get("ENGINE", "django_omnitenant.backends.postgresql"),
            "NAME": db_config.get("NAME") or base_config.get("NAME"),
            "USER": db_config.get("USER") or base_config.get("USER"),
            "PASSWORD": db_config.get("PASSWORD") or base_config.get("PASSWORD"),
            "HOST": db_config.get("HOST") or base_config.get("HOST"),
            "PORT": db_config.get("PORT") or base_config.get("PORT"),
            "OPTIONS": db_config.get("OPTIONS") or base_config.get("OPTIONS", {}),
            "TIME_ZONE": db_config.get("TIME_ZONE")
            or base_config.get("TIME_ZONE", settings.TIME_ZONE),
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
            "TEST": db_config.get("TEST")
            if "TEST" in db_config
            else base_config.get("TEST", {}),
        }

        return db_alias, resolved_config

    def bind(self):
        db_alias, db_config = self.get_alias_and_config(self.tenant)
        settings.DATABASES[db_alias] = db_config
        print(f"Database with alias {db_alias} added to settings.DATABASES.")

    def activate(self):
        db_alias = self.db_config.get("ALIAS") or self.db_config.get("NAME")
        if db_alias not in settings.DATABASES:
            self.bind()
        TenantContext.push_db_alias(db_alias)

    def deactivate(self):
        TenantContext.pop_db_alias()
