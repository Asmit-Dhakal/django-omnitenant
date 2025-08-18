from django_omnitenant.exceptions import DomainNotFound
from django_omnitenant.models import BaseDomain
from django_omnitenant.utils import get_domain_model
from .base import BaseTenantResolver


class CustomDomainTenantResolver(BaseTenantResolver):
    def resolve(self, request) -> object | None:
        host_name = request.get_host().split(":")[0]  # Remove port if present
        if host_name.startswith("www."):
            host_name = host_name[4:]

        Domain: BaseDomain = get_domain_model()  # type: ignore
        try:
            return Domain.objects.get(domain=host_name).tenant
        except Domain.DoesNotExist:
            raise DomainNotFound
