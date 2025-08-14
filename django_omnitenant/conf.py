from django.conf import settings as django_settings
from django.utils.functional import cached_property
from .constants import constants

class _WrappedSettings:
    def __getattr__(self, item):
        return getattr(django_settings, item)

    def __setattr__(self, key, value):
        if key in self.__dict__:
            raise ValueError("Item assignment is not supported")

        setattr(django_settings, key, value)

    @cached_property
    def OMNITENANT_CONFIG(self)->dict:
        return getattr(django_settings, constants.OMNITENANT_CONFIG, {})
    
    @cached_property
    def SCHEMA_CONFIG(self)->dict:
        return self.OMNITENANT_CONFIG.get(constants.SCHEMA_CONFIG, {})
    
    @cached_property
    def TENANT_RESOLVER(self)->str:
        return self.OMNITENANT_CONFIG.get(constants.TENANT_RESOLVER, "django_omnitenant.resolvers.SubdomainTenantResolver")
    
    @cached_property
    def TIME_ZONE(self)->str:
        return getattr(django_settings, "TIME_ZONE", "UTC")
    

    @cached_property
    def PUBLIC_SCHEMA_NAME(self)->str:
       return self.SCHEMA_CONFIG.get(constants.PUBLIC_SCHEMA_NAME, 'public')
    
    
settings = _WrappedSettings()
