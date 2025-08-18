from django.utils.functional import cached_property


class _Constants:
    @cached_property
    def TENANT_MODEL(self) -> str:
        return "TENANT_MODEL"
    
    @cached_property
    def DOMAIN_MODEL(self) -> str:
        return "DOMAIN_MODEL"


    @cached_property
    def OMNITENANT_CONFIG(self) -> str:
        return "OMNITENANT_CONFIG"

    @cached_property
    def TENANT_RESOLVER(self) -> str:
        return "TENANT_RESOLVER"

    @cached_property
    def DEFAULT_DB_ALIAS(self) -> str:
        return "default"

    @cached_property
    def SCHEMA_CONFIG(self) -> str:
        return "schema_config"

    @cached_property
    def PUBLIC_SCHEMA_NAME(self) -> str:
        return "PUBLIC_SCHEMA_NAME"
    
    @cached_property
    def DEFAULT_CACHE_ALIAS(self) -> str:
        return "default"
    
    @cached_property
    def DEFAULT_HOST(self) -> str:
        return "DEFAULT_HOST"
    
    @cached_property
    def PATCHES(self) -> str:
        return "PATCHES"


constants = _Constants()
