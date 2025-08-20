from django_omnitenant.conf import settings
from requests.structures import CaseInsensitiveDict

from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.constants import constants


class CacheTenantBackend:
    def __init__(self, tenant):
        self.tenant = tenant
        self.cache_config: CaseInsensitiveDict = CaseInsensitiveDict(
            self.tenant.config.get("cache_config", {})
        )

    @classmethod
    def get_alias_and_config(cls, tenant):
        """
        Returns the cache alias and resolved configuration for the tenant.
        """
        cache_config = CaseInsensitiveDict(tenant.config.get("cache_config", {}))

        cache_alias = cache_config.get("ALIAS") or tenant.tenant_id
        base_config = settings.CACHES.get(constants.DEFAULT_CACHE_ALIAS, {}).copy()

        resolved_config = {
            "BACKEND": cache_config.get("BACKEND")
            or base_config.get("BACKEND", "django_redis.cache.RedisCache"),
            "LOCATION": cache_config.get("LOCATION") or base_config.get("LOCATION"),
            "TIMEOUT": cache_config.get("TIMEOUT") or base_config.get("TIMEOUT", 86400),
            "OPTIONS": cache_config.get("OPTIONS") or base_config.get("OPTIONS", {}),
            "IS_USING_DEFAULT_CONFIG": not cache_config,
        }

        return cache_alias, resolved_config

    def bind(self):
        cache_alias, cache_config = self.get_alias_and_config(self.tenant)
        settings.CACHES[cache_alias] = cache_config
        print(f"Cache with alias {cache_alias} added to settings.CACHES.")

    def activate(self):
        cache_alias, _ = self.get_alias_and_config(self.tenant)
        if cache_alias not in settings.CACHES:
            self.bind()
        TenantContext.push_cache_alias(cache_alias)

    def deactivate(self):
        TenantContext.pop_cache_alias()
