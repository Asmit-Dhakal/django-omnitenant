from django_omnitenant.utils import get_tenant_model
from .base import BaseTenantResolver
from django_omnitenant.constants import constants

class SubdomainTenantResolver(BaseTenantResolver):
    def resolve(self, request) -> object | None:
        host = request.get_host().split(".")[0]
        tenant = get_tenant_model()
        try:
            return tenant.objects.get(tenant_id=host)
        except tenant.DoesNotExist:
            return None
