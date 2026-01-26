"""
Tenant Middleware for django-omnitenant

This module provides the central middleware component responsible for tenant resolution
and context management in a multi-tenant Django application.

The TenantMiddleware intercepts each request, determines the current tenant based on
the request (using a configurable resolver), and establishes the tenant context for
the entire request lifecycle.

Key Responsibilities:
    1. Dynamically load and instantiate the configured tenant resolver
    2. Resolve the current tenant from each incoming request
    3. Establish and maintain tenant context throughout the request
    4. Handle domain resolution failures gracefully
    5. Set the tenant on the request object for downstream access

Architecture:
    - Uses Django's MiddlewareMixin for compatibility with Django's middleware system
    - Loads resolver class dynamically based on settings.TENANT_RESOLVER
    - Implements context management using TenantContext for thread-safe tenant isolation
    - Provides automatic fallback to PUBLIC_TENANT for requests from public hosts

Configuration:
    The middleware is configured through Django settings:

    MIDDLEWARE = [
        # ... other middleware
        'django_omnitenant.middleware.TenantMiddleware',
    ]

    OMNITENANT_CONFIG = {
        'TENANT_RESOLVER': 'myapp.resolvers.CustomResolver',
        'PUBLIC_HOST': 'example.com',
        'PUBLIC_TENANT_NAME': 'public',
    }

Usage:
    The middleware is automatically executed by Django for every request so that the current tenant can be accessed in the
     views:

    ```python
    def my_view(request):
        current_tenant = request.tenant
        # Use current_tenant for database queries, etc.
    ```

Error Handling:
    - Invalid domains return a 400 JSON response
    - Public host requests fall back to the public tenant
    - Resolver import errors are raised with descriptive messages

Related Components:
    - TenantContext: Manages thread-local tenant context
    - Resolvers: Components that determine tenant from request
    - conf.py: Configuration and settings management
"""

from importlib import import_module
from typing import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from django_omnitenant.exceptions import DomainNotFound, TenantNotFound

from .conf import settings
from .models import BaseTenant
from .tenant_context import TenantContext
from .utils import get_tenant_model


class TenantMiddleware(MiddlewareMixin):
    """
    Django middleware for resolving and managing tenant context.

    This middleware is the core component that enables multi-tenancy in django-omnitenant.
    It executes on every request to:
    1. Determine the current tenant based on the request
    2. Set up the tenant context for the request lifecycle
    3. Attach the tenant to the request object

    The middleware uses a pluggable resolver pattern, allowing different tenant resolution
    strategies (subdomain-based, custom domain-based, header-based, etc.) to be configured
    without changing the middleware code.

    Attributes:
        resolver: Instance of the tenant resolver class configured in settings

    Lifecycle:
        - __init__: Loads and instantiates the resolver class
        - __call__: Processes each request to resolve tenant and set context

    Configuration:
        settings.TENANT_RESOLVER: Dotted path to resolver class (e.g., 'app.resolvers.SubdomainResolver')
        settings.PUBLIC_HOST: Domain name for public/shared content
        settings.PUBLIC_TENANT_NAME: Identifier of the public tenant

    Examples:
        In Django settings:

        ```python
        MIDDLEWARE = [
            # ... other middleware
            'django_omnitenant.middleware.TenantMiddleware',
        ]

        OMNITENANT_CONFIG = {
            'TENANT_RESOLVER': 'myapp.resolvers.SubdomainResolver',
            'PUBLIC_HOST': 'example.com',
            'PUBLIC_TENANT_NAME': 'public',
        }
        ```

        In views:

        ```python
        def my_view(request):
            tenant = request.tenant  # Automatically set by middleware
            # Perform tenant-scoped operations
            return Response({'tenant': str(tenant)})
        ```

    Raises:
        Exception: If the resolver class cannot be imported or instantiated

    Note:
        This middleware must be placed before any middleware that accesses tenant-specific
        data to ensure the tenant context is properly established.
    """

    def __init__(
        self, get_response: Callable[[HttpRequest], HttpResponse] | None = ...
    ) -> None:
        """
        Initialize the TenantMiddleware and load the configured resolver.

        This constructor dynamically imports and instantiates the resolver class
        specified in settings.TENANT_RESOLVER. The resolver is responsible for
        determining which tenant a request belongs to.

        Args:
            get_response: Callable that handles the request after middleware processing.
                         Provided by Django's middleware loading mechanism.

        Raises:
            Exception: If the resolver module or class cannot be found, or if
                      instantiation fails. The error message includes details about
                      the import failure.

        Process:
            1. Parse the dotted path: 'module.path.ClassName' -> ('module.path', 'ClassName')
            2. Import the module
            3. Extract the class from the module
            4. Instantiate the resolver
            5. Call parent __init__ with get_response

        Example:
            If settings.TENANT_RESOLVER = 'myapp.resolvers.SubdomainResolver',
            this will import myapp.resolvers and instantiate SubdomainResolver()
        """
        # Parse resolver class path: "module.path.ClassName" -> ("module.path", "ClassName")
        module_name, class_name = settings.TENANT_RESOLVER.rsplit(".", 1)

        try:
            # Dynamically import the resolver module
            module = import_module(module_name)
        except Exception as e:
            # Provide clear error message if resolver cannot be imported
            raise Exception(
                f"Unable to import resolver {settings.TENANT_RESOLVER} due to: {e}"
            )

        # Get the resolver class from the imported module
        resolver_class = getattr(module, class_name)

        # Instantiate the resolver
        self.resolver = resolver_class()

        # Call parent class initializer
        super().__init__(get_response)

    def __call__(self, request):
        """
        Process the incoming request to resolve and set the current tenant.

        This method is called for every incoming request. It:
        1. Uses the resolver to determine the current tenant
        2. Sets up the tenant context
        3. Attaches the tenant to the request
        4. Processes the request through the rest of the middleware/view chain
        5. Cleans up the tenant context after response is generated

        Args:
            request (HttpRequest): The incoming HTTP request

        Returns:
            HttpResponse: The response from the rest of the middleware/view chain,
                         or a 400 JSON error response if the domain is invalid

        Process:
            1. Try to resolve tenant using the configured resolver
            2. If resolution fails:
               - Check if request is from public host (settings.PUBLIC_HOST)
               - If yes: Create public tenant instance
               - If no: Return 400 error response
            3. Set up tenant context using context manager
            4. Attach tenant to request object
            5. Process request through rest of chain
            6. Return response (context automatically cleaned up)

        Examples:
            Successful tenant resolution (subdomain.example.com):
            - Resolver finds tenant for subdomain
            - Tenant context established
            - request.tenant = tenant object

            Public host request (example.com):
            - Resolver fails to find specific tenant
            - Detects PUBLIC_HOST match
            - Falls back to public tenant
            - request.tenant = public tenant object

            Invalid domain (random-domain.com):
            - Resolver fails to find tenant
            - Host doesn't match PUBLIC_HOST
            - Returns {"detail": "Invalid Domain"} with 400 status

        Exceptions:
            DomainNotFound: Raised by resolver when domain is invalid
            TenantNotFound: Raised by resolver when tenant cannot be located

        Note:
            The TenantContext.use_tenant() context manager ensures that:
            - The tenant is set in thread-local storage
            - Database routers can direct queries to correct database
            - The tenant is automatically cleaned up after response
        """
        try:
            # Attempt to resolve tenant from the request using the configured resolver
            tenant: BaseTenant = self.resolver.resolve(request)
        except (DomainNotFound, TenantNotFound):
            # Resolver couldn't determine tenant - handle fallback logic

            # Extract host from request (remove port if present: "example.com:8000" -> "example.com")
            host = request.get_host().split(":")[0]

            # Check if request is from the public/main host
            if host == settings.PUBLIC_HOST:
                # Create a public tenant instance for requests to the main domain
                TenantModel = get_tenant_model()
                tenant: BaseTenant = TenantModel(
                    name=settings.PUBLIC_TENANT_NAME,
                    tenant_id=settings.PUBLIC_TENANT_NAME,
                    isolation_type=BaseTenant.IsolationType.DATABASE,
                )  # type: ignore
            else:
                # Request is from an unknown domain - return error response
                return JsonResponse({"detail": "Invalid Domain"}, status=400)

        # Establish tenant context and process the request
        # TenantContext.use_tenant() is a context manager that:
        # - Sets tenant in thread-local storage
        # - Ensures database router routes queries to correct database
        # - Automatically cleans up after the request
        with TenantContext.use_tenant(tenant):
            # Attach tenant to request object for downstream access in views and other middleware
            request.tenant = tenant

            # Process request through rest of middleware chain and view
            response = self.get_response(request)

        # Context manager exits here, tenant context is automatically cleaned up
        return response
