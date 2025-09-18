from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model

from .conf import settings
from .constants import constants
from .utils import get_tenant_model


class _BootStrapper:
    def __init__(self):
        self._patches: list[str] = [
            "django_omnitenant.patches.cache",
            "django_omnitenant.patches.celery",
        ]

    def _parse(self):
        """
        Parse the OMNITENANT_CONFIG to extract patches and other settings.
        """
        patches = settings.OMNITENANT_CONFIG.get(constants.PATCHES, self._patches)

        if not isinstance(patches, list) and not isinstance(patches, tuple):
            raise ImproperlyConfigured(
                f"OMNITENANT_CONFIG['{constants.PATCHES}'] must be a list of patch module paths."
            )
        if isinstance(patches, tuple):
            patches = list(patches)

        self._patches.extend(patches)

    def _run_validation(self) -> None:
        tenant_model_path: str = settings.OMNITENANT_CONFIG.get(
            constants.TENANT_MODEL, ""
        )
        if not tenant_model_path:
            raise ImproperlyConfigured(
                f"OMNITENANT_CONFIG must define '{constants.TENANT_MODEL}'. Example:\n"
                f"OMNITENANT_CONFIG = {{ '{constants.TENANT_MODEL}': 'myapp.Tenant' }}"
            )
        try:
            model = get_tenant_model()
        except LookupError:
            raise ImproperlyConfigured(
                f"Could not find tenant model '{tenant_model_path}'. "
                f"Check your OMNITENANT_CONFIG in settings.py."
            )

        # Ensure model is a Django model subclass
        if not issubclass(model, Model):
            raise ImproperlyConfigured(
                f"{tenant_model_path} is not a valid Django model."
            )

        default_host: str = settings.OMNITENANT_CONFIG.get(constants.DEFAULT_HOST, "")
        if not default_host:
            raise ImproperlyConfigured(
                f"OMNITENANT_CONFIG must define '{constants.DEFAULT_HOST}'. Example:\n"
                f"OMNITENANT_CONFIG = {{ '{constants.DEFAULT_HOST}': 'localhost' }}"
            )

    def _run_patches(self):
        for patch in self._patches:
            try:
                import_module(patch)
            except Exception as e:
                raise Exception(
                    "Unable to import patch module {patch} due to: {exc_info}".format(
                        patch=patch, exc_info=e
                    )
                )

    def run(self):
        self._parse()
        self._run_validation()
        self._run_patches()


app_bootstrapper = _BootStrapper()
