from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model

from .conf import settings
from .constants import constants
from .utils import get_tenant_model

class DjangoOmnitenantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_omnitenant'
    
    def ready(self):
        tenant_model_path: str = settings.OMNITENANT_CONFIG.get(constants.TENANT_MODEL, "")
        if not tenant_model_path:
            raise ImproperlyConfigured(
                f"OMNITENANT_CONFIG must define '{constants.TENANT_MODEL}'. Example:\n"
                f"OMNITENANT_CONFIG = {{ '{constants.TENANT_MODEL}': 'myapp.Tenant' }}"
            )
        try:
            model = get_tenant_model()
        except LookupError :
            raise ImproperlyConfigured(
                f"Could not find tenant model '{tenant_model_path}'. "
                f"Check your OMNITENANT_CONFIG in settings.py."
            )

        # Ensure model is a Django model subclass
        if not issubclass(model, Model):
            raise ImproperlyConfigured(
                f"{tenant_model_path} is not a valid Django model."
            ) 
        
    # TODO: If default db engine is django.db.backends.postgresql.base then change it to django_omnitenant.backends.postgresql
