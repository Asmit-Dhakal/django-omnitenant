"""Admin helpers for multi-tenant projects.

This module contains logic to restrict access to certain Django admin
models so they are only visible and editable from the master tenant.
The typical use-case might be the project where a subset of
models (for example global configuration, billing plans, or shared
resources) should only be managed at a single, centrally-administered
tenant and hidden from per-tenant admin interfaces.

How it works
------------
- The `TenantRestrictAdminMixin` is mixed into existing
  ModelAdmin classes at import time for selected models.
- For those models the mixin overrides permission checks and model
  visibility so that only the configured master tenant may see and
  operate on them.
- Models are selected for restriction if any of the following are true:
  - the app config defines ``master_managed = True``
  - the model class defines ``master_managed = True``
  - the model class defines ``tenant_managed = False`` (i.e. not tenant-scoped)

Configuration
-------------
- The master tenant name is read from ``settings.MASTER_TENANT_NAME``.
- The list of apps to inspect comes from :func:`get_custom_apps` which
  allows consumers to control which installed apps are evaluated.

Notes for maintainers
---------------------
- This module runs at import time and mutates ``admin.site`` by
  unregistering and re-registering ModelAdmin classes. Import order
  matters: it is important this module is imported after apps have
  been loaded and their ModelAdmin registrations have occurred.
  Thus `django_omnitenant` must be placed after all the custom defined apps in the project in the INSTALLED_APPS.
"""

from django.apps import apps
from django.contrib import admin

from .conf import settings
from .models import BaseTenant
from .utils import get_custom_apps


class TenantRestrictAdminMixin(admin.ModelAdmin):
    """A small mixin that restricts admin access to the master tenant.

    This mixin is intentionally minimal: it overrides the standard
    ModelAdmin permission checks to return permissive results only when
    the current request is served under the master tenant. When the
    request's tenant is not the master tenant, the mixin denies
    visibility and all CRUD permissions so the model is hidden from the
    non-master tenant's admin UI.

    Implementation details
    ----------------------
    - ``_is_master_tenant``: helper that inspects ``request.tenant`` and
      compares its ``name`` to ``settings.MASTER_TENANT_NAME``. It is
      small and isolated so it can be overridden in tests if necessary.
    - Each of the permission hooks used by Django admin
      (``get_model_perms``, ``has_*_permission``) delegates to
      ``_is_master_tenant`` to make the logic explicit and consistent.

    Override considerations
    -----------------------
    If a project needs finer-grained control (for example allowing
    view-only access to non-master tenants) you can extend this mixin
    and override the individual ``has_*_permission`` methods.
    """

    def _is_master_tenant(self, request):
        """Return ``True`` when the current request belongs to the master tenant.

        Args:
            request: the HTTP request object passed by Django admin.

        Returns:
            ``True`` if ``request.tenant.name`` equals
            ``settings.MASTER_TENANT_NAME``; ``False`` otherwise.
        """

        tenant: BaseTenant = request.tenant
        return tenant.name == settings.MASTER_TENANT_NAME

    def get_model_perms(self, request):
        """Return the model permissions dictionary for the current request.

        When not in the master tenant an empty dict is returned which
        causes Django admin to hide the model from the index/listing.
        """

        if self._is_master_tenant(request):
            return super().get_model_perms(request)
        return {}

    def has_module_permission(self, request):
        """Whether the model module should be visible in the admin index."""

        return self._is_master_tenant(request)

    def has_view_permission(self, request, obj=None):
        """Whether ``request`` can view instances of this model."""

        return self._is_master_tenant(request)

    def has_add_permission(self, request):
        """Whether ``request`` can add new instances of this model."""

        return self._is_master_tenant(request)

    def has_change_permission(self, request, obj=None):
        """Whether ``request`` can modify the given object (or any object)."""

        return self._is_master_tenant(request)

    def has_delete_permission(self, request, obj=None):
        """Whether ``request`` can delete the given object (or any object)."""

        return self._is_master_tenant(request)


# Determine which apps to inspect for models that require master-only admin
app_names = get_custom_apps()

# Walk each app's models and, when a model is configured as master-managed
# or explicitly not tenant-managed, unregister any existing admin and
# re-register it using a dynamically created admin class that mixes in
# ``_TenantRestrictAdminMixin``. This keeps the original ModelAdmin
# behavior while adding the master-only restriction.
for app_name in app_names:
    app_config = apps.get_app_config(app_name)
    is_app_master_managed = getattr(app_config, "master_managed", False)

    for model in app_config.get_models():
        # Selection rules: restrict when the app declares master management,
        # when the model declares master management, or when the model is
        # explicitly not tenant-managed (shared/global model).
        if (
            is_app_master_managed
            or getattr(model, "master_managed", False)
            or not getattr(model, "tenant_managed", True)
        ):
            # If the model already has a registered ModelAdmin we keep its
            # behavior by using its type as the base; otherwise fall back to
            # Django's ``ModelAdmin``. We must unregister the existing
            # registration before re-registering the modified admin class.
            if admin.site.is_registered(model):
                original_admin = type(admin.site._registry[model])
                admin.site.unregister(model)
            else:
                original_admin = admin.ModelAdmin

            # Create a new ModelAdmin subclass combining the restriction mixin
            # and the original admin, preserving any customizations that may
            # have been applied by the project's admin modules.
            RestrictedAdmin = type(
                f"{model.__name__}RestrictedAdmin",
                (TenantRestrictAdminMixin, original_admin),
                {},
            )
            admin.site.register(model, RestrictedAdmin)
