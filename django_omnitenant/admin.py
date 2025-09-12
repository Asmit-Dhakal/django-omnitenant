from django.apps import apps
from django.contrib import admin
from .conf import settings
from .models import BaseTenant
from .utils import get_custom_apps



class _DefaultTenantOnlyAdmin(admin.ModelAdmin):
    """
    Internal admin to hide models outside the default tenant.
    """

    def _is_default_tenant(self, request):
        tenant: BaseTenant = request.tenant
        return tenant.name == settings.PUBLIC_SCHEMA_NAME

    def get_model_perms(self, request):
        if self._is_default_tenant(request):
            return {}
        return super().get_model_perms(request)

    def has_module_permission(self, request):
        return self._is_default_tenant(request)

    def has_view_permission(self, request, obj=None):
        return self._is_default_tenant(request)

    def has_add_permission(self, request):
        return self._is_default_tenant(request)

    def has_change_permission(self, request, obj=None):
        return self._is_default_tenant(request)

    def has_delete_permission(self, request, obj=None):
        return self._is_default_tenant(request)


app_names = get_custom_apps()

for app_name in app_names:
    app_config = apps.get_app_config(app_name)
    if not getattr(app_config, "tenant_managed", True):
        for model in app_config.get_models():
            if admin.site.is_registered(model):
                admin.site.unregister(model)
            admin.site.register(model, _DefaultTenantOnlyAdmin)
    else:
        for model in app_config.get_models():
            if getattr(model, "globally_managed", False):
                continue
            if not getattr(model, "tenant_managed", True):
                if admin.site.is_registered(model):
                    admin.site.unregister(model)
                admin.site.register(model, _DefaultTenantOnlyAdmin)
            