from django.apps import apps
from django.conf import settings
from .tenant_context import TenantContext
from .constants import constants
from .utils import get_custom_apps

class TenantRouter:
    def _is_tenant_model(self, model):
        # Only apply tenant logic for custom apps
        if model._meta.app_label not in get_custom_apps():
            return True  # treat non-custom apps as tenant-managed by default

        # 1. Check AppConfig
        app_config = apps.get_app_config(model._meta.app_label)
        if hasattr(app_config, "tenant_managed"):
            return getattr(app_config, "tenant_managed", True)

        # 2. Check Model 
        return getattr(model, "tenant_managed", True)

    def db_for_read(self, model, **hints):
        if not self._is_tenant_model(model):
            return constants.DEFAULT_DB_ALIAS
        return TenantContext.get_db_alias() or constants.DEFAULT_DB_ALIAS

    def db_for_write(self, model, **hints):
        if not self._is_tenant_model(model):
            return constants.DEFAULT_DB_ALIAS
        return TenantContext.get_db_alias() or constants.DEFAULT_DB_ALIAS

    def allow_relation(self, obj1, obj2, **hints):
        return len({self.db_for_read(obj1), self.db_for_read(obj2)}) == 1

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Only apply tenant logic for custom apps
        if app_label not in get_custom_apps():
            return True  # allow migrations for non-custom apps everywhere

        if not model_name:
            try:
                app_config = apps.get_app_config(app_label)
            except LookupError:
                return None
            if hasattr(app_config, "tenant_managed") and not getattr(
                app_config, "tenant_managed", True
            ):
                return db == constants.DEFAULT_DB_ALIAS
            return db != constants.DEFAULT_DB_ALIAS

        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return None

        if not self._is_tenant_model(model):
            return db == constants.DEFAULT_DB_ALIAS
        return db != constants.DEFAULT_DB_ALIAS
