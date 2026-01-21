from django_omnitenant.exceptions import TenantNotFound
from django_omnitenant.utils import get_tenant_model
from .base import BaseTenantResolver


class SubdomainTenantResolver(BaseTenantResolver):
    def resolve(self, request) -> object | None:
        subdomain = request.get_host().split(".")[0]
        Tenant = get_tenant_model()
        try:
            return Tenant.objects.get(tenant_id=subdomain)
        except Tenant.DoesNotExist:
            raise TenantNotFound
