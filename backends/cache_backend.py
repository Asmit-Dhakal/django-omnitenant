"""
Cache-per-Tenant Backend Module

This module implements cache isolation for multi-tenant applications where each
tenant gets its own isolated cache namespace.

Cache Backend Purpose:
    The cache backend manages tenant-specific cache configurations, allowing:
    - Separate cache storage per tenant
    - Different cache settings per tenant (TTL, backend, location)
    - Cache isolation to prevent cross-tenant data leakage
    - Dynamic cache registration in Django's CACHES setting

Cache Configuration:
    Tenants can specify cache configuration in their config:

    ```python
    tenant.config = {
        'cache_config': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://tenant-redis.example.com:6379/0',
            'ALIAS': 'acme_cache',            # Optional
            'TIMEOUT': 3600,                  # Optional, default 86400
            'OPTIONS': {'PARSER': 'hiredis'}, # Optional
        }
    }
    ```

Cache Isolation Strategies:
    1. Separate Redis Instances (Strongest)
       - Each tenant has their own Redis instance
       - Complete isolation at infrastructure level
       - Higher resource usage

    2. Separate Redis Databases (Recommended)
       - All tenants share Redis instance
       - Different database number per tenant (redis://host:6379/0, /1, /2)
       - Good isolation with shared resources

    3. Separate Key Prefixes (Basic)
       - All tenants share same Redis database
       - Prefix all keys with tenant_id
       - Must be enforced by application code
       - Least isolated but resource efficient

Cache Lifecycle:
    1. __init__() - Initialize backend with tenant config
    2. get_alias_and_config() - Build resolved cache configuration
    3. bind() - Register cache in Django's CACHES setting
    4. activate() - Switch to tenant's cache for context
    5. deactivate() - Exit tenant cache context

Usage Example:
    ```python
    from django_omnitenant.backends.cache_backend import CacheTenantBackend
    from django_omnitenant.tenant_context import TenantContext
    from myapp.models import Tenant

    # Create tenant with cache config
    tenant = Tenant.objects.create(
        tenant_id='acme',
        config={
            'cache_config': {
                'LOCATION': 'redis://redis.example.com:6379/0',
                'ALIAS': 'acme_cache',
            }
        }
    )

    # Activate tenant cache
    backend = CacheTenantBackend(tenant)
    backend.bind()

    with TenantContext.use_tenant(tenant):
        # Cache operations use tenant's cache
        from django.core.cache import cache
        cache.set('key', 'value', timeout=3600)
        value = cache.get('key')
    ```

Related:
    - tenant_context.py: Context management for cache switching
    - conf.py: Configuration system for cache settings
    - constants.py: MASTER_CACHE_ALIAS and other constants
"""

from django_omnitenant.conf import settings
from requests.structures import CaseInsensitiveDict

from django_omnitenant.tenant_context import TenantContext


class CacheTenantBackend:
    """
    Cache-per-Tenant backend for managing tenant-specific caches.

    This backend manages cache configuration and isolation for multi-tenant
    applications, allowing each tenant to have its own cache storage with
    independent settings.

    Unlike database and schema backends which inherit from BaseTenantBackend,
    the cache backend is simpler and doesn't require complex lifecycle management:
    - No creation/deletion operations needed
    - Caches are registered dynamically at runtime
    - Configuration-driven rather than state-driven

    Key Features:
        - Dynamic cache registration in Django's CACHES setting
        - Per-tenant cache configuration
        - Cache isolation via separate storage/keys
        - Lazy cache binding
        - Context-based cache switching

    Configuration Resolution:
        Similar to database backend, cache config is resolved as:
        1. Tenant-specific setting (highest priority)
        2. Master cache setting (from MASTER_CACHE_ALIAS)
        3. Django default (lowest priority)

    Cache Alias:
        Each cache has an alias used in Django's CACHES setting:
        - Explicit: tenant.config['cache_config']['ALIAS']
        - Default: tenant.tenant_id
        - Used with cache.get_cache(alias) or settings.CACHES[alias]

    Attributes:
        tenant (BaseTenant): The tenant instance
        cache_config (CaseInsensitiveDict): Tenant's cache configuration
    """

    def __init__(self, tenant):
        """
        Initialize cache backend for a tenant.

        Args:
            tenant (BaseTenant): Tenant instance to manage cache for

        Process:
            1. Store tenant reference
            2. Extract cache configuration from tenant.config
            3. Use CaseInsensitiveDict for case-insensitive lookups

        The cache_config is extracted from tenant.config['cache_config'],
        defaulting to empty dict if not configured.

        CaseInsensitiveDict allows:
        - cache_config['ALIAS'] and cache_config['alias'] both work
        - Flexible configuration lookup
        - Case-insensitive key access

        Example:
            ```python
            tenant = Tenant.objects.create(
                tenant_id='acme',
                config={
                    'cache_config': {
                        'BACKEND': 'django_redis.cache.RedisCache',
                        'LOCATION': 'redis://localhost:6379/0',
                    }
                }
            )

            backend = CacheTenantBackend(tenant)
            # backend.cache_config now contains the configuration
            # backend.cache_config['backend'] works (case-insensitive)
            ```
        """
        self.tenant = tenant
        # Extract cache configuration from tenant config, defaulting to empty dict
        # CaseInsensitiveDict allows flexible lookups regardless of key casing
        self.cache_config: CaseInsensitiveDict = CaseInsensitiveDict(
            self.tenant.config.get("cache_config", {})
        )

    @classmethod
    def get_alias_and_config(cls, tenant):
        """
        Build and return the cache alias and fully resolved configuration for a tenant.

        This class method constructs the complete Django cache configuration by merging
        tenant-specific settings with master cache defaults. The result is a ready-to-use
        cache configuration dictionary.

        Process:
            1. Extract tenant's cache_config from tenant.config['cache_config']
            2. Determine cache alias (from ALIAS, or default to tenant_id)
            3. Get base configuration from master cache
            4. Merge tenant config with base, with tenant taking precedence
            5. Ensure all required fields have defaults

        Args:
            tenant (BaseTenant): Tenant instance to get cache config for

        Returns:
            tuple: (cache_alias, resolved_config)
            - cache_alias (str): Cache alias for use in Django CACHES setting
            - resolved_config (dict): Complete Django cache configuration dict

        Configuration Precedence:
            For each setting, resolved config uses:
            1. Tenant's cache_config value if present
            2. Master cache value if tenant doesn't override
            3. Django default if neither specified

            Example resolution:
            ```
            TENANT cache_config: {'LOCATION': 'redis://tenant.local:6379/0'}
            MASTER CACHES:       {'LOCATION': 'redis://master.local:6379/0', 'TIMEOUT': 3600}
            RESULT:              {'LOCATION': 'redis://tenant.local:6379/0', 'TIMEOUT': 3600}
            ```

        Alias Determination:
            Cache alias is resolved in order:
            1. tenant.config['cache_config']['ALIAS'] - Explicit alias (preferred)
            2. tenant.tenant_id - Use tenant_id as alias (default)

            Example:
            ```python
            # With explicit ALIAS
            tenant1.config = {'cache_config': {'ALIAS': 'acme_cache'}}
            alias, _ = get_alias_and_config(tenant1)
            assert alias == 'acme_cache'

            # Without explicit ALIAS
            tenant2.tenant_id = 'globex'
            alias, _ = get_alias_and_config(tenant2)
            assert alias == 'globex'
            ```

        Configuration Fields:
            The resolved config includes:

            - BACKEND: Cache backend class
              (django_redis.cache.RedisCache, django.core.cache.backends.locmem.LocMemCache, etc.)

            - LOCATION: Cache storage location
              (redis://host:port/db, /tmp/django_cache, memcache_host:port, etc.)

            - TIMEOUT: Default cache timeout in seconds
              (86400 = 24 hours by default)

            - OPTIONS: Backend-specific options
              (parser, client_class, serializer, pool_kwargs, etc.)

            - IS_USING_DEFAULT_CONFIG: Whether using default config
              (True if no tenant-specific cache_config provided)

        Master Cache Configuration:
            The base config comes from settings.MASTER_CACHE_ALIAS:
            - Provides defaults for all tenant caches
            - Typically shared cache infrastructure
            - Can be overridden per-tenant

        Examples:
            ```python
            # Minimal tenant config (uses master defaults)
            tenant.config = {'cache_config': {}}
            alias, config = get_alias_and_config(tenant)
            # Uses master backend, location, timeout, etc.

            # Tenant-specific location (separate Redis DB)
            tenant.config = {
                'cache_config': {
                    'LOCATION': 'redis://redis.example.com:6379/1',
                }
            }
            alias, config = get_alias_and_config(tenant)
            # Uses tenant's location, master's backend, timeout, etc.

            # Completely custom config
            tenant.config = {
                'cache_config': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                    'LOCATION': 'unique-snowflake',
                    'ALIAS': 'acme_locmem',
                    'TIMEOUT': 3600,
                }
            }
            alias, config = get_alias_and_config(tenant)
            # Uses all tenant-specific settings
            ```

        Performance:
            This is a fast operation (dict merging):
            - Called during bind() and activate()
            - No external API calls
            - No database queries
            - O(1) operation complexity

        See Also:
            - __init__(): Uses cache_config from tenant
            - bind(): Uses returned config to register cache
            - activate(): Uses alias for context switching
        """
        cache_config = CaseInsensitiveDict(tenant.config.get("cache_config", {}))

        # Determine cache alias: explicit ALIAS takes precedence over tenant_id
        # If not provided, use tenant_id as the cache alias
        cache_alias = cache_config.get("ALIAS") or tenant.tenant_id

        # Get base configuration from master cache as defaults
        # Master cache is configured in settings.MASTER_CACHE_ALIAS
        # We'll use it as fallback for any settings not explicitly set for this tenant
        base_config = settings.CACHES.get(settings.MASTER_CACHE_ALIAS, {}).copy()

        # Build resolved configuration by merging tenant settings with master defaults
        # Tenant settings take precedence (override master settings)
        resolved_config = {
            # BACKEND: Cache backend implementation to use
            # Defaults to django_redis.cache.RedisCache if not specified
            # Can be any Django cache backend or custom implementation
            "BACKEND": cache_config.get("BACKEND")
            or base_config.get("BACKEND", "django_redis.cache.RedisCache"),
            # LOCATION: Where the cache stores data
            # For Redis: "redis://host:port/db" or "unix:///tmp/redis.sock"
            # For Memcache: "127.0.0.1:11211"
            # For LocMem: "unique-string"
            "LOCATION": cache_config.get("LOCATION") or base_config.get("LOCATION"),
            # TIMEOUT: Default cache timeout in seconds
            # 86400 = 24 hours
            # Can be overridden per key with cache.set(key, value, timeout=X)
            "TIMEOUT": cache_config.get("TIMEOUT") or base_config.get("TIMEOUT", 86400),
            # OPTIONS: Backend-specific options
            # For Redis: PARSER, CLIENT_CLASS, SOCKET_CONNECT_TIMEOUT, etc.
            # For others: depends on backend
            "OPTIONS": cache_config.get("OPTIONS") or base_config.get("OPTIONS", {}),
            # IS_USING_DEFAULT_CONFIG: Flag indicating if using default/master config
            # True if no tenant-specific cache_config provided
            # False if tenant provided explicit configuration
            "IS_USING_DEFAULT_CONFIG": not cache_config,
        }

        return cache_alias, resolved_config

    def bind(self):
        """
        Register tenant's cache in Django's CACHES setting.

        This method makes the tenant's cache available to Django for cache operations.
        After bind() is called, the cache can be accessed via:
        - cache.get_cache(alias) or caches[alias]
        - Within TenantContext (automatic routing)

        Process:
            1. Get cache alias and resolved configuration via get_alias_and_config()
            2. Add/register cache in Django's CACHES setting
            3. Print confirmation for logging

        Effect:
            After bind() completes:
            - Cache is in settings.CACHES[cache_alias]
            - Cache operations can target it explicitly
            - TenantContext can route to it
            - Django's cache framework recognizes it

        Configuration:
            The configuration is built by merging:
            - Tenant-specific cache settings
            - Master cache defaults
            - Django built-in defaults

        Idempotency:
            Calling bind() multiple times is safe:
            - Later calls overwrite previous registration
            - No errors if cache alias already exists
            - Can be used to update cache configuration

        Use Cases:
            bind() is called during:
            - Initialization when first accessing tenant cache
            - activate() for lazy cache registration
            - Manual cache setup

        Dynamic Registration:
            Unlike static CACHES configuration in settings.py:
            - Caches registered at runtime
            - Allows multiple tenants without pre-configuration
            - Supports dynamic cache creation
            - Flexible cache topology per tenant

        Examples:
            ```python
            tenant = Tenant.objects.create(
                tenant_id='acme',
                config={
                    'cache_config': {
                        'LOCATION': 'redis://redis.example.com:6379/0',
                    }
                }
            )

            backend = CacheTenantBackend(tenant)

            # Register the cache
            backend.bind()

            # Now cache is available
            assert 'acme' in settings.CACHES

            # Can use it
            from django.core.cache import cache
            cache_instance = caches['acme']
            cache_instance.set('key', 'value')
            ```

        Error Handling:
            Errors can occur from:
            - Invalid backend
            - Invalid location (Redis unreachable, etc.)
            - Missing required settings

            These typically happen at first cache access, not at bind().

        See Also:
            - get_alias_and_config(): Build cache configuration
            - activate(): Lazy binding before context activation
            - deactivate(): Does not remove cache (just context exit)
        """
        # Get the cache alias and fully resolved configuration
        # Merges tenant-specific settings with master cache defaults
        cache_alias, cache_config = self.get_alias_and_config(self.tenant)

        # Register the cache in Django's CACHES setting
        # Now it's available for all cache operations
        settings.CACHES[cache_alias] = cache_config

        # Log the binding for visibility and debugging
        print(f"Cache with alias {cache_alias} added to settings.CACHES.")

    def activate(self):
        """
        Activate the tenant's cache for the current context.

        This method makes the tenant's cache the active cache for subsequent
        operations within the context. Uses TenantContext to manage cache switching.

        Process:
            1. Get tenant's cache alias and configuration
            2. If cache not yet registered, bind() it (lazy registration)
            3. Push cache alias onto context stack via TenantContext

        Lazy Binding:
            If the cache isn't already in Django's CACHES setting, activate() calls
            bind() to register it. This allows:
            - Caches to be created on-demand
            - No need to pre-register all tenant caches
            - Efficient resource usage

        Context Stack:
            Uses TenantContext.push_cache_alias() to maintain a stack of active caches:
            - Supports nested tenant contexts
            - Proper cleanup on context exit
            - Thread-local so safe for concurrent requests
            - Django's cache framework can route to correct cache

        Lifecycle:
            Called when:
            - Entering TenantContext context manager
            - Request middleware activates tenant for request
            - Explicitly switching cache context

        Effect:
            After activate(), cache operations use tenant's cache:

            ```python
            from django.core.cache import cache

            backend.activate()
            cache.set('key', 'value')  # Uses tenant's cache, not master
            value = cache.get('key')   # Gets from tenant's cache
            ```

        Comparison to Database/Schema Backends:
            Unlike database backends:
            - No complex state management needed
            - No schema/connection switching
            - Just pushes cache alias to context stack
            - Very lightweight operation

        Examples:
            ```python
            from django_omnitenant.tenant_context import TenantContext

            # Automatic via context manager (preferred)
            with TenantContext.use_tenant(tenant):
                # activate() called automatically
                from django.core.cache import cache
                cache.set('key', 'value')  # Uses tenant cache
                # deactivate() called automatically

            # Manual usage
            backend.activate()
            try:
                cache.set('key', 'value')
            finally:
                backend.deactivate()
            ```

        Performance:
            activate() is called for every request/context:
            - Very fast (just pushes to stack)
            - Lazy binds cache if needed
            - Minimal overhead
            - No expensive operations

        Thread Safety:
            TenantContext uses thread-local storage:
            - Each request thread has independent context
            - Concurrent requests don't interfere
            - Safe for multi-threaded application servers

        Error Handling:
            If cache configuration is invalid:
            - Error occurs at first cache access, not at activate()
            - activate() just sets up the context
            - Caller catches errors from cache.get/set operations

        See Also:
            - deactivate(): Exit cache context
            - bind(): Register cache in Django
            - TenantContext: Context manager for activation
            - get_alias_and_config(): Build cache configuration
        """
        # Get the cache alias for this tenant
        cache_alias, _ = self.get_alias_and_config(self.tenant)

        # Ensure cache is registered in Django settings
        # Lazy bind if not already done (e.g., if activate() before explicit bind())
        if cache_alias not in settings.CACHES:
            self.bind()

        # Push cache alias onto context stack
        # TenantContext maintains a stack for nested context support
        # Enables automatic cache routing within the context
        TenantContext.push_cache_alias(cache_alias)

    def deactivate(self):
        """
        Exit the tenant's cache context and restore previous cache context.

        This method pops the cache alias from the context stack, restoring
        the previous cache context. This happens at the end of a request or
        when explicitly exiting a TenantContext.

        Process:
            1. Pop cache alias from TenantContext stack

        Effect:
            After deactivate(), previous cache becomes active:

            ```python
            # Tenant context (cache_alias='acme')
            backend1.activate()
            cache.set('key', 'value1')  # Uses acme cache

            backend1.deactivate()
            cache.set('key', 'value2')  # Uses previous cache
            ```

        Context Stack Management:
            Pops the cache alias from the stack maintained by TenantContext:
            - Supports nested tenant contexts
            - Previous cache is restored
            - Stack underflow is handled by TenantContext

        Lifecycle:
            Called when:
            - Exiting TenantContext context manager
            - Request middleware finishes request processing
            - Explicitly exiting cache context

        Exception Safety:
            deactivate() should always be called, similar to try/finally:

            ```python
            backend.activate()
            try:
                dangerous_operation()  # May raise exception
            finally:
                backend.deactivate()  # Always called
            ```

        Comparison to Database/Schema Backends:
            Unlike database backends:
            - No schema restoration needed
            - No database connection switching
            - Just simple stack pop
            - Very lightweight cleanup

        Nested Contexts:
            Supports nested tenant cache contexts:

            ```python
            with TenantContext.use_tenant(tenant1):
                # Activates tenant1 cache
                cache.set('key', 'v1')

                with TenantContext.use_tenant(tenant2):
                    # Activates tenant2 cache
                    cache.set('key', 'v2')
                    # Deactivates, back to tenant1

                # Deactivates, back to previous cache
            ```

            Each deactivate() restores the context from the previous level.

        Error Handling:
            If deactivate() fails:
            - Exception is raised
            - Stack is still affected (pop was attempted)
            - Caller should handle gracefully

            Unlikely to fail in normal operation.

        Performance:
            deactivate() is very fast:
            - Single stack pop operation
            - O(1) complexity
            - No expensive operations
            - Called for every request

        Thread Safety:
            TenantContext uses thread-local storage:
            - Each thread maintains independent stack
            - deactivate() in one thread doesn't affect others
            - Safe for concurrent request processing

        Examples:
            ```python
            from django_omnitenant.tenant_context import TenantContext

            # Automatic via context manager (preferred)
            with TenantContext.use_tenant(tenant):
                # activate() called
                cache.set('key', 'value')
                # deactivate() called automatically

            # Manual usage
            backend.activate()
            try:
                cache.set('key', 'value')
            finally:
                backend.deactivate()  # Always called
            ```

        See Also:
            - activate(): Push cache alias onto context stack
            - TenantContext: Context manager for cache management
            - Context stack: Maintains cache routing state
        """
        # Pop cache alias from context stack
        # Restores the previous cache for any parent context
        TenantContext.pop_cache_alias()
