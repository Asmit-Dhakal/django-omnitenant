"""
Tenant Resolver Base Module

This module defines the abstract interface for tenant resolution - the process of
determining which tenant a request belongs to based on request properties.

Tenant Resolution Concept:
    In a multi-tenant application, each request must be associated with a specific
    tenant. The resolver examines the request and identifies the tenant.
    
    Example: A request to "acme.example.com" should resolve to the "acme" tenant.
    
Resolver Purpose:
    A resolver examines request properties and returns the corresponding Tenant:
    - Examines request headers, host, path, cookies, etc.
    - Queries the Tenant/Domain models to find matching tenant
    - Returns the Tenant instance for the request
    - Returns None if no matching tenant found (404 or shared tenant)
    
Resolution Strategies:
    Different resolvers implement different identification strategies:
    
    1. Subdomain-based (SubdomainTenantResolver)
       - Tenant from subdomain: "acme.example.com" → tenant_id='acme'
       - Works with wildcard DNS
       - Common for SaaS applications
       
    2. Custom domain-based (CustomDomainTenantResolver)
       - Tenant from custom domain: "acme.com" → tenant with custom domain
       - Each tenant can have custom branded domain
       - Requires DNS management per tenant
       
    3. Path-based (Custom implementation)
       - Tenant from URL path: "/acme/..." → tenant_id='acme'
       - Requires path prefix in all URLs
       - Less common in modern applications
       
    4. Header-based (Custom implementation)
       - Tenant from request header: "X-Tenant-ID: acme"
       - Useful for APIs
       - Requires client to specify tenant
       
Resolver Integration:
    The resolver is configured in Django settings:
    
    ```python
    OMNITENANT_CONFIG = {
        'TENANT_RESOLVER': 'path.to.CustomResolver',
    }
    ```
    
    Then used by middleware:
    
    ```python
    from django.utils.decorators import middleware_decorator
    from django_omnitenant.middleware import TenantMiddleware
    
    # TenantMiddleware dynamically imports and instantiates the resolver
    # Then calls resolver.resolve(request) for each request
    ```
    
Request Properties Available for Resolution:
    Different resolver implementations examine:
    
    - request.META['HTTP_HOST']: The requested host/domain
    - request.path: The URL path
    - request.META['HTTP_REFERER']: Referrer header
    - request.META.get('HTTP_X_TENANT_ID'): Custom headers
    - request.method: HTTP method
    - request.GET/POST: Query parameters
    - request.COOKIES: Session/cookie data
    - request.user: Authenticated user (if available)
    
Tenant Model:
    The resolver queries the Tenant model:
    
    ```python
    from django_omnitenant.utils import get_tenant_model
    
    Tenant = get_tenant_model()
    tenant = Tenant.objects.get(tenant_id='acme')  # Example
    ```
    
    Or uses Domain model for domain-based resolution:
    
    ```python
    from django_omnitenant.utils import get_domain_model
    
    Domain = get_domain_model()
    domain = Domain.objects.get(domain='acme.example.com')
    tenant = domain.tenant
    ```

Error Handling:
    Resolvers should handle errors gracefully:
    
    - Tenant not found: Return None (middleware handles as 404)
    - Multiple matches: Raise or return first match
    - Database errors: Propagate or return None
    - Invalid request: Return None (shared tenant or 404)
    
Performance:
    Tenant resolution happens on every request:
    - Should be fast (cache query results)
    - Database queries should use select_related/prefetch
    - Cache tenant lookups if possible
    - Avoid N+1 query problems
    
Caching:
    Resolution results can be cached:
    
    ```python
    from django.core.cache import cache
    
    cache_key = f'tenant:{request.META["HTTP_HOST"]}'
    tenant = cache.get(cache_key)
    if not tenant:
        tenant = self._resolve_tenant(request)
        cache.set(cache_key, tenant, timeout=3600)
    return tenant
    ```
    
Usage Flow:
    1. Request arrives at application
    2. Middleware.process_request() is called
    3. TenantMiddleware instantiates resolver
    4. Calls resolver.resolve(request)
    5. Resolver examines request and returns Tenant
    6. TenantContext activated with resolved tenant
    7. Request processing continues with tenant context
    8. TenantMiddleware.process_response() cleans up context
    
Custom Resolver Implementation:
    Implement by subclassing BaseTenantResolver:
    
    ```python
    from django_omnitenant.resolvers.base import BaseTenantResolver
    from django_omnitenant.utils import get_tenant_model
    
    class MyResolver(BaseTenantResolver):
        def resolve(self, request):
            # Your custom resolution logic
            tenant_id = self._extract_tenant_id(request)
            if not tenant_id:
                return None
            
            Tenant = get_tenant_model()
            try:
                return Tenant.objects.get(tenant_id=tenant_id)
            except Tenant.DoesNotExist:
                return None
    ```
    
Related:
    - middleware.py: Uses resolver to identify tenant
    - subdomain_resolver.py: Subdomain-based resolution
    - customdomain_resolver.py: Custom domain-based resolution
    - tenant_context.py: Activates resolved tenant context
"""


class BaseTenantResolver:
    """
    Abstract base class for tenant resolution from HTTP requests.
    
    A tenant resolver examines an HTTP request and determines which tenant
    the request belongs to. This is the core abstraction for multi-tenant
    request routing.
    
    Subclasses implement different resolution strategies:
    - Subdomain-based: Tenant from request.META['HTTP_HOST']
    - Custom domain: Tenant from Domain model lookup
    - Path-based: Tenant from request.path
    - Header-based: Tenant from request headers
    - Custom logic: Application-specific resolution
    
    Key Responsibilities:
        1. Examine request properties
        2. Query Tenant/Domain models
        3. Return Tenant instance or None
        4. Handle errors gracefully
        5. Be performant (called on every request)
        
    Resolution Output:
        - Returns: Tenant instance (non-None) → Request is for that tenant
        - Returns: None → No matching tenant or shared/public data
        
        When None is returned, middleware typically:
        - Uses public/master tenant as fallback
        - Returns 404 Not Found
        - Redirects to default tenant
        - Serves shared/public content
        
    Integration:
        Middleware uses resolver:
        
        ```python
        from django_omnitenant.middleware import TenantMiddleware
        
        # TenantMiddleware internally:
        resolver = instantiate_resolver()  # From TENANT_RESOLVER setting
        tenant = resolver.resolve(request)
        if tenant:
            TenantContext.activate(tenant)
        ```
        
    Performance Considerations:
        - Called on every request
        - Should use database caching/optimization
        - Consider caching resolver results
        - Avoid N+1 query problems
        - Keep resolution logic fast
        
    Thread Safety:
        - Resolver instances are created per request
        - No shared state between requests
        - Thread-safe by design
        
    Attributes:
        None (state is passed via request parameter)
        
    Abstract Methods:
        - resolve(request): Must be implemented by subclasses
    """

    def resolve(self, request):
        """
        Resolve the tenant for the given request.
        
        Examines the request and determines which tenant it belongs to.
        
        This is an abstract method that must be implemented by subclasses.
        Each subclass implements a specific resolution strategy.
        
        Args:
            request (django.http.HttpRequest): The HTTP request to resolve
                                              Contains headers, host, path, cookies, etc.
        
        Returns:
            BaseTenant or None: 
                - BaseTenant instance: Tenant was successfully identified
                - None: No matching tenant (shared/public or 404)
                
        Raises:
            NotImplementedError: Always raised by base class
                                Subclasses must override this method
                                
        Request Properties Available for Inspection:
            - request.META['HTTP_HOST']: Requested host/domain
            - request.path: URL path component
            - request.method: HTTP method (GET, POST, etc.)
            - request.GET: Query parameters (?key=value)
            - request.POST: POST form data
            - request.COOKIES: Session and other cookies
            - request.META.get('HTTP_X_TENANT_ID'): Custom headers
            - request.user: Authenticated user (if available)
            - request.session: Session data
            - request.environ: Raw WSGI environment
            - request.FILES: Uploaded files
            
        Implementation Examples:
            
            Subdomain-based resolver:
            ```python
            class SubdomainResolver(BaseTenantResolver):
                def resolve(self, request):
                    host = request.META['HTTP_HOST'].lower()
                    # host = 'acme.example.com'
                    
                    # Extract subdomain
                    parts = host.split('.')
                    if len(parts) > 2:
                        tenant_id = parts[0]  # 'acme'
                    else:
                        return None  # No subdomain
                    
                    Tenant = get_tenant_model()
                    try:
                        return Tenant.objects.get(tenant_id=tenant_id)
                    except Tenant.DoesNotExist:
                        return None
            ```
            
            Custom domain resolver:
            ```python
            class CustomDomainResolver(BaseTenantResolver):
                def resolve(self, request):
                    host = request.META['HTTP_HOST'].lower()
                    
                    Domain = get_domain_model()
                    try:
                        domain = Domain.objects.select_related('tenant').get(
                            domain=host
                        )
                        return domain.tenant
                    except Domain.DoesNotExist:
                        return None
            ```
            
            Path-based resolver:
            ```python
            class PathResolver(BaseTenantResolver):
                def resolve(self, request):
                    path = request.path  # '/acme/dashboard/'
                    parts = path.split('/')
                    
                    if len(parts) < 2:
                        return None
                    
                    tenant_id = parts[1]  # 'acme'
                    
                    Tenant = get_tenant_model()
                    try:
                        return Tenant.objects.get(tenant_id=tenant_id)
                    except Tenant.DoesNotExist:
                        return None
            ```
            
            Header-based resolver:
            ```python
            class HeaderResolver(BaseTenantResolver):
                def resolve(self, request):
                    tenant_id = request.META.get('HTTP_X_TENANT_ID')
                    if not tenant_id:
                        return None
                    
                    Tenant = get_tenant_model()
                    try:
                        return Tenant.objects.get(tenant_id=tenant_id)
                    except Tenant.DoesNotExist:
                        return None
            ```
            
            Cached resolver:
            ```python
            class CachedResolver(BaseTenantResolver):
                def resolve(self, request):
                    host = request.META['HTTP_HOST']
                    cache_key = f'tenant:{host}'
                    
                    tenant = cache.get(cache_key)
                    if tenant is None:
                        tenant = self._resolve_uncached(request)
                        if tenant:
                            cache.set(cache_key, tenant, timeout=3600)
                    
                    return tenant
                
                def _resolve_uncached(self, request):
                    # Actual resolution logic
                    pass
            ```
            
        Return Value Semantics:
            
            Non-None return:
            - Request is for this specific tenant
            - All subsequent operations in tenant context
            - Tables accessed from tenant schema/database
            - Middleware activates TenantContext with this tenant
            
            None return:
            - No matching tenant found
            - Could mean:
              - Unknown subdomain/domain
              - Missing required identifier
              - Request for shared/public content
              - Shared tenant operations
            - Middleware behavior configurable:
              - Use public tenant
              - Return 404
              - Redirect to default tenant
            
        Error Handling:
            
            Resolver should handle gracefully:
            
            ```python
            def resolve(self, request):
                try:
                    tenant_id = self._extract_tenant_id(request)
                    if not tenant_id:
                        return None
                    
                    Tenant = get_tenant_model()
                    return Tenant.objects.get(tenant_id=tenant_id)
                
                except Tenant.DoesNotExist:
                    return None  # Unknown tenant
                
                except Exception as e:
                    logger.error(f"Tenant resolution failed: {e}")
                    return None  # Error during resolution
            ```
            
        Performance Notes:
            - Called on every request - must be fast
            - Use select_related() for foreign keys
            - Use prefetch_related() for reverse relations
            - Consider caching results
            - Minimize database queries
            
        Testing:
            
            ```python
            class TestMyResolver(TestCase):
                def test_resolve_existing_tenant(self):
                    tenant = Tenant.objects.create(tenant_id='acme')
                    
                    request = RequestFactory().get('/')
                    request.META['HTTP_HOST'] = 'acme.example.com'
                    
                    resolver = MyResolver()
                    result = resolver.resolve(request)
                    
                    assert result == tenant
                
                def test_resolve_missing_tenant(self):
                    request = RequestFactory().get('/')
                    request.META['HTTP_HOST'] = 'unknown.example.com'
                    
                    resolver = MyResolver()
                    result = resolver.resolve(request)
                    
                    assert result is None
            ```
            
        Configuration:
            Resolver is configured in Django settings:
            
            ```python
            OMNITENANT_CONFIG = {
                'TENANT_RESOLVER': 'myapp.resolvers.CustomResolver',
            }
            ```
            
        See Also:
            - middleware.py: Uses resolver for request routing
            - subdomain_resolver.py: Subdomain-based implementation
            - customdomain_resolver.py: Custom domain implementation
            - tenant_context.py: Activates resolved tenant
            - utils.get_tenant_model(): Access Tenant model
            - utils.get_domain_model(): Access Domain model
        """
        raise NotImplementedError
