"""
Configuration Constants module for django-omnitenant

This module provides a centralized management system for all configuration key constants
used throughout the django-omnitenant package. It implements a singleton pattern using a
_Constants class with cached properties to ensure consistent access to configuration keys
across the application.

The module serves as the single source of truth for all configuration setting keys,
eliminating hardcoded strings throughout the codebase and promoting maintainability,
type safety, and consistency.

Usage:
    from django_omnitenant.constants import constants

    # Access a configuration key
    tenant_model_key = constants.TENANT_MODEL

    # Use in Django settings
    from django.conf import settings
    tenant_model = settings.OMNITENANT_CONFIG[constants.TENANT_MODEL]

Design Patterns:
    - Singleton Pattern: Module-level `constants` instance ensures single source of truth
    - Cached Properties: @cached_property provides lazy initialization and caching
    - String-Based Keys: Constants return strings used as dictionary keys in OMNITENANT_CONFIG

Performance:
    - Constants are computed only once per application lifetime
    - Thread-safe for multithreaded environments
    - Minimal overhead with O(1) lookup on subsequent accesses
"""

from django.utils.functional import cached_property


class _Constants:
    """
    Private class that manages all configuration key constants for django-omnitenant.

    Uses Django's @cached_property decorator to lazily initialize and cache constant
    values. This class should not be instantiated directly; use the module-level
    `constants` singleton instance instead.

    Key Features:
        - Lazy Initialization: Constants created only when first accessed
        - Caching: Values cached after first access for performance
        - Type Hints: All properties explicitly return str type
        - Centralized Management: All configuration keys defined in one location
    """

    @cached_property
    def TENANT_MODEL(self) -> str:
        """
        Configuration key for the custom tenant model class path.

        Returns:
            str: Setting key "TENANT_MODEL"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            tenant_model_path = settings.OMNITENANT_CONFIG[constants.TENANT_MODEL]
            # e.g., "myapp.Tenant"
        """
        return "TENANT_MODEL"

    @cached_property
    def DOMAIN_MODEL(self) -> str:
        """
        Configuration key for the custom domain model class path.

        Returns:
            str: Setting key "DOMAIN_MODEL"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            domain_model_path = settings.OMNITENANT_CONFIG[constants.DOMAIN_MODEL]
            # e.g., "myapp.Domain"
        """
        return "DOMAIN_MODEL"

    @cached_property
    def OMNITENANT_CONFIG(self) -> str:
        """
        Configuration key for the main omnitenant configuration dictionary.

        This is the primary setting key containing all django-omnitenant configuration
        in Django settings.

        Returns:
            str: Setting key "OMNITENANT_CONFIG"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            omnitenant_config = getattr(settings, constants.OMNITENANT_CONFIG, {})
        """
        return "OMNITENANT_CONFIG"

    @cached_property
    def TENANT_RESOLVER(self) -> str:
        """
        Configuration key for the tenant resolver implementation class.

        Specifies which resolver class is used to determine the current tenant based
        on incoming requests (e.g., subdomain resolver, custom domain resolver).

        Returns:
            str: Setting key "TENANT_RESOLVER"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            resolver_class = settings.OMNITENANT_CONFIG[constants.TENANT_RESOLVER]
            # e.g., "myapp.resolvers.SubdomainResolver"
        """
        return "TENANT_RESOLVER"

    @cached_property
    def PUBLIC_DB_ALIAS(self) -> str:
        """
        Configuration key for the public/shared database alias.

        Specifies the database alias used for shared data across all tenants that is
        not isolated per-tenant.

        Returns:
            str: Setting key "PUBLIC_DB_ALIAS"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            public_db = settings.OMNITENANT_CONFIG[constants.PUBLIC_DB_ALIAS]
            # e.g., "default"
        """
        return "PUBLIC_DB_ALIAS"

    @cached_property
    def MASTER_DB_ALIAS(self) -> str:
        """
        Configuration key for the master database alias.

        Specifies the database alias for the master/default database that contains
        core system data and tenant records.

        Returns:
            str: Setting key "MASTER_DB_ALIAS"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            master_db = settings.OMNITENANT_CONFIG[constants.MASTER_DB_ALIAS]
            # e.g., "master"
        """
        return "MASTER_DB_ALIAS"

    @cached_property
    def SCHEMA_CONFIG(self) -> str:
        """
        Configuration key for schema-based multi-tenancy configuration.

        Used for schema-based isolation approach where each tenant has its own
        database schema (typically with PostgreSQL).

        Returns:
            str: Setting key "schema_config"

        Note:
            This constant returns "schema_config" (lowercase) unlike other constants
            which use UPPERCASE keys.
        """
        return "schema_config"

    @cached_property
    def PUBLIC_TENANT_NAME(self) -> str:
        """
        Configuration key for the public tenant identifier.

        Specifies the name/identifier of the public tenant which contains shared
        data accessible to all tenants.

        Returns:
            str: Setting key "PUBLIC_TENANT_NAME"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            public_tenant_name = settings.OMNITENANT_CONFIG[constants.PUBLIC_TENANT_NAME]
            # e.g., "public"
        """
        return "PUBLIC_TENANT_NAME"
    
    @cached_property
    def TEST_TENANT_NAME(self) -> str:
        """
        Configuration key for the test tenant identifier.

        Specifies the name/identifier of the test tenant which contains
        data for the testing.

        Returns:
            str: Setting key "TEST_TENANT_NAME"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            test_tenant_name = settings.OMNITENANT_CONFIG[constants.TEST_TENANT_NAME]
            # e.g., "public"
        """
        return "TEST_TENANT_NAME"


    @cached_property
    def MASTER_TENANT_NAME(self) -> str:
        """
        Configuration key for the master/default tenant identifier.

        Specifies the name/identifier of the master tenant which is typically used
        for the main administrative or system tenant.

        Returns:
            str: Setting key "MASTER_TENANT_NAME"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            master_tenant_name = settings.OMNITENANT_CONFIG[constants.MASTER_TENANT_NAME]
            # e.g., "master"
        """
        return "MASTER_TENANT_NAME"

    @cached_property
    def DEFAULT_SCHEMA_NAME(self) -> str:
        """
        Configuration key for the default schema name.

        Specifies the default database schema name used for schema-based isolation
        when no specific schema is set for a tenant.

        Returns:
            str: Setting key "DEFAULT_SCHEMA_NAME"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            default_schema = settings.OMNITENANT_CONFIG[constants.DEFAULT_SCHEMA_NAME]
            # e.g., "public"
        """
        return "DEFAULT_SCHEMA_NAME"

    @cached_property
    def MASTER_CACHE_ALIAS(self) -> str:
        """
        Configuration key for the cache backend alias used for master/global caching.

        Specifies which cache backend alias is used for caching data that applies
        across all tenants (master cache).

        Returns:
            str: Setting key "DEFAULT_CACHE_ALIAS"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            master_cache = settings.OMNITENANT_CONFIG[constants.MASTER_CACHE_ALIAS]
            # e.g., "default"
        """
        return "DEFAULT_CACHE_ALIAS"

    @cached_property
    def PUBLIC_HOST(self) -> str:
        """
        Configuration key for the public/main hostname.

        Specifies the main hostname for the public or primary application domain.

        Returns:
            str: Setting key "PUBLIC_HOST"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            public_host = settings.OMNITENANT_CONFIG[constants.PUBLIC_HOST]
            # e.g., "example.com"
        """
        return "PUBLIC_HOST"

    @cached_property
    def PATCHES(self) -> str:
        """
        Configuration key for optional patches/customizations to apply.

        Specifies a list of optional patches or customizations that should be
        applied to the core django-omnitenant functionality.

        Returns:
            str: Setting key "PATCHES"

        Usage:
            from django.conf import settings
            from django_omnitenant.constants import constants

            patches = settings.OMNITENANT_CONFIG.get(constants.PATCHES, [])
            # e.g., ["cache", "celery"]
        """
        return "PATCHES"


constants = _Constants()
"""
Singleton instance of _Constants providing the public API for configuration keys.

This module-level instance should be used throughout the application to access
configuration constants. Using the singleton ensures consistent, single-source-of-truth
access to all configuration keys.

Best Practices:
    - Always import and use this singleton instance, never instantiate _Constants directly
    - Use this instead of hardcoding configuration key strings
    - Reference this in all code that accesses django-omnitenant configuration

Examples:
    from django_omnitenant.constants import constants
    
    # In settings configuration
    OMNITENANT_CONFIG = {
        constants.TENANT_MODEL: "myapp.Tenant",
        constants.DOMAIN_MODEL: "myapp.Domain",
        constants.PUBLIC_TENANT_NAME: "public",
        constants.MASTER_TENANT_NAME: "master",
        constants.TENANT_RESOLVER: "myapp.resolvers.CustomResolver",
        constants.PUBLIC_DB_ALIAS: "default",
        constants.MASTER_DB_ALIAS: "master",
        constants.PUBLIC_HOST: "example.com",
    }
    
    # In application code
    from django.conf import settings
    from django_omnitenant.constants import constants
    
    tenant_model = settings.OMNITENANT_CONFIG[constants.TENANT_MODEL]
"""
