from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from importlib import import_module

from django_omnitenant.exceptions import TenantNotFound
from .tenant_context import TenantContext
from .conf import settings
from .models import BaseTenant


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
        try:
            tenant: BaseTenant = self.resolver.resolve(request)
        except TenantNotFound:
            host = request.get_host()
            parts = host.split(".")
            if len(parts) > 2:
                base_domain = ".".join(parts[1:])
            else:
                base_domain = host
            return redirect(f"{request.scheme}://{base_domain}")

        with TenantContext.use(tenant):
            request.tenant = tenant
            response = self.get_response(request)

        return response
