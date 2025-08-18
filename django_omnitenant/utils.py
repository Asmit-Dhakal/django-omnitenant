from django.apps import apps
from .conf import settings
from .constants import constants
from django.db.models.base import Model


def get_tenant_model() -> type[Model]:
    return apps.get_model(settings.TENANT_MODEL)

def get_domain_model() -> type[Model]:
    return apps.get_model(settings.DOMAIN_MODEL) 


def get_custom_apps() -> list[str]:
    """
    Return a list of custom apps within the project (excluding built-in and third-party apps).
    """
    if hasattr(settings, "CUSTOM_APPS"):
        return settings.CUSTOM_APPS

    custom_apps = []
    base_dir_str = str(settings.BASE_DIR)

    for app_config in apps.get_app_configs():
        if app_config.path.startswith(base_dir_str):
            custom_apps.append(app_config.name)

    return custom_apps
