from django.apps import apps
from django.contrib import admin

from .conf import settings
from .models import BaseTenant
from .utils import get_custom_apps


class _TenantRestrictAdminMixin(admin.ModelAdmin):
    """
    Internal admin to hide models outside the default tenant.
    """

    def _is_default_tenant(self, request):
        tenant: BaseTenant = request.tenant
        return tenant.name == settings.DEFAULT_TENANT_NAME

    def get_model_perms(self, request):
        if self._is_default_tenant(request):
            return super().get_model_perms(request)
        return {}

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
    for model in app_config.get_models():
        if not getattr(model, "tenant_managed", True) and not getattr(
            model, "globally_managed", False
        ):
            # Get the currently registered admin (if any)
            if admin.site.is_registered(model):
                original_admin = type(admin.site._registry[model])
                admin.site.unregister(model)
            else:
                original_admin = admin.ModelAdmin

            # Dynamically create a new admin class that mixes in the restrictions
            RestrictedAdmin = type(
                f"{model.__name__}RestrictedAdmin",
                (_TenantRestrictAdminMixin, original_admin),
                {},
            )
            admin.site.register(model, RestrictedAdmin)
