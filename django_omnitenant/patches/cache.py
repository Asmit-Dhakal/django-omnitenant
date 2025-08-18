# django_omnitenant/patches/cache.py

from django.core.cache import CacheHandler as DjangoCacheHandler
from django_omnitenant.tenant_context import TenantContext
import django.core.cache
from django_omnitenant.conf import settings


class TenantAwareCacheWrapper:
    """
    Wraps a Django cache backend to be tenant-aware.
    Adds tenant key prefix if using the default backend.
    """

    def __init__(self, handler: DjangoCacheHandler):
        self._handler = handler

    def _get_cache(self):
        alias = TenantContext.get_cache_alias() or "default"
        if alias in self._handler:
            return self._handler[alias]
        return self._handler["default"]

    def _prefixed_key(self, key):
        """
        Prefix key with tenant_id if using default cache.
        """
        alias = TenantContext.get_cache_alias() or "default"
        if settings.CACHES[alias]["IS_USING_DEFAULT_CONFIG"]:
            tenant_id = (
                TenantContext.get_tenant().tenant_id
                if TenantContext.get_tenant()
                else None
            )
            if tenant_id is not None:
                return f"{tenant_id}:{key}"
        return key

    # --- Standard cache methods ---
    def __getitem__(self, key):
        return self._get_cache()[self._prefixed_key(key)]

    def __setitem__(self, key, value):
        self._get_cache()[self._prefixed_key(key)] = value

    def __delitem__(self, key):
        del self._get_cache()[self._prefixed_key(key)]

    def __contains__(self, key):
        return self._prefixed_key(key) in self._get_cache()

    def __getattr__(self, name):
        # For methods like get, set, delete, etc.
        cache = self._get_cache()
        attr = getattr(cache, name)
        if callable(attr):
            # Wrap set/get/delete to add prefix automatically
            def wrapper(*args, **kwargs):
                if name in ("get", "set", "delete", "has_key"):
                    if args:
                        args = (self._prefixed_key(args[0]), *args[1:])
                return attr(*args, **kwargs)

            return wrapper
        return attr

    # --- Django expects this ---
    def close_all(self):
        for alias in self._handler:
            backend = self._handler[alias]
            if hasattr(backend, "close"):
                backend.close()


def patch_django_cache():
    """
    Patch Django caches so that django.core.cache.cache and caches become tenant-aware.
    """
    original_handler = DjangoCacheHandler()
    tenant_aware_wrapper = TenantAwareCacheWrapper(original_handler)

    django.core.cache.caches = tenant_aware_wrapper
    django.core.cache.cache = tenant_aware_wrapper


patch_django_cache()
