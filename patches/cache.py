import django.core.cache
from django.core.cache import CacheHandler as DjangoCacheHandler

from django_omnitenant.conf import settings
from django_omnitenant.tenant_context import TenantContext


class TenantAwareCacheWrapper:
    """
    Wraps Django caches to be tenant-aware.
    Automatically prefixes keys with tenant_id for the default cache.
    """

    def __init__(self, handler: DjangoCacheHandler):
        self._handler = handler

    def _get_cache(self):
        alias = TenantContext.get_cache_alias() or "default"
        try:
            return self._handler[alias]
        except KeyError:
            return self._handler["default"]

    def _apply_prefix(self, key):
        """
        Apply tenant prefix if using default cache.
        """
        alias = TenantContext.get_cache_alias() or "default"
        if settings.CACHES[alias].get("IS_USING_DEFAULT_CONFIG", True):
            tenant = TenantContext.get_tenant()
            if tenant is not None:
                return f"{tenant.tenant_id}:{key}"
        return key

    # --- Dict-style access ---
    def __getitem__(self, key):
        return self._get_cache().get(self._apply_prefix(key))

    def __setitem__(self, key, value):
        self._get_cache().set(self._apply_prefix(key), value)

    def __delitem__(self, key):
        deleted = self._get_cache().delete(self._apply_prefix(key))
        if not deleted:
            raise KeyError(key)

    def __contains__(self, key):
        return self._get_cache().get(self._apply_prefix(key)) is not None

    # --- Attribute access (methods like get, set, delete, etc.) ---
    def __getattr__(self, name):
        cache = self._get_cache()
        attr = getattr(cache, name)

        if callable(attr):

            def wrapper(*args, **kwargs):
                if not args:
                    return attr(*args, **kwargs)

                # Single-key methods
                if name in {
                    "get",
                    "set",
                    "add",
                    "delete",
                    "has_key",
                    "incr",
                    "decr",
                    "touch",
                    "get_or_set",
                }:
                    args = (self._apply_prefix(args[0]), *args[1:])

                # No need to apply prefix for these because keys method will be called before these methods whill will already apply the prefix so just call these methods without applying prefix
                # Multi-key methods
                # elif name in {"get_many", "delete_many"}:
                # keys = args[0]
                # args = ([self._apply_prefix(k) for k in keys], *args[1:])

                # Dict-of-keys method
                # elif name == "set_many":
                #     mapping = args[0]
                #     new_mapping = {self._apply_prefix(k): v for k, v in mapping.items()}
                #     args = (new_mapping, *args[1:])

                # Pattern-based
                elif name == "keys":
                    args = (self._apply_prefix(args[0]), *args[1:])

                return attr(*args, **kwargs)

            return wrapper

        return attr

    # --- Django expects this ---
    def close_all(self):
        for alias in getattr(self._handler, "_caches", {}):
            backend = self._handler[alias]
            if hasattr(backend, "close"):
                backend.close()


def patch_django_cache():
    """
    Patch Django caches so that django.core.cache.cache and caches become tenant-aware.
    """
    original_handler = DjangoCacheHandler()
    tenant_aware_wrapper = TenantAwareCacheWrapper(original_handler)

    # Patch the main module references
    django.core.cache.caches = tenant_aware_wrapper
    django.core.cache.cache = tenant_aware_wrapper

    # Patch the internal ConnectionProxy target so all lazy accesses go through wrapper
    if hasattr(django.core.cache, "_connections"):
        for name in ("cache", "caches"):
            if name in django.core.cache._connections:
                django.core.cache._connections[name] = tenant_aware_wrapper


patch_django_cache()
