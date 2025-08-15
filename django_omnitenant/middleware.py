from typing import Callable
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.db.models.base import Model
from importlib import import_module
from .tenant_context import TenantContext
from .conf import settings
from .models import BaseTenant


from .backends import BaseTenantBackend, SchemaTenantBackend, DatabaseTenantBackend


class TenantMiddleware(MiddlewareMixin):
    def __init__(
        self, get_response: Callable[[HttpRequest], HttpResponse] | None = ...
    ) -> None:
        module_name, class_name = settings.TENANT_RESOLVER.rsplit(".", 1)
        try:
            module = import_module(module_name)
        except Exception as e:
            raise Exception(
                f"Unable to import resolver {settings.TENANT_RESOLVER} due to: {e}"
            )

        resolver_class = getattr(module, class_name)
        self.resolver = resolver_class()

        super().__init__(get_response)

    def __call__(self, request):
        tenant: BaseTenant | None = self.resolver.resolve(request)

        if tenant:
            TenantContext.set_tenant(tenant)
            request.tenant = tenant

            backend: BaseTenantBackend = (
                SchemaTenantBackend(tenant)
                if tenant.isolation_type == BaseTenant.IsolationType.SCHEMA
                else DatabaseTenantBackend(tenant)
            )
            backend.activate()
        #TODO: else: Set default tenant so request.tenant gives a default tenant 


        response = self.get_response(request)

        if tenant:
            backend.deactivate()
            TenantContext.clear_tenant()
        return response
