from django.apps import apps
from .conf import settings
from .constants import constants
from django.db.models.base import Model


def get_tenant_model() -> type[Model]:
    return apps.get_model(settings.OMNITENANT_CONFIG.get(constants.TENANT_MODEL))
