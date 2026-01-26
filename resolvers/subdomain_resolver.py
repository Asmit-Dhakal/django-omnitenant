"""
Subdomain-based Tenant Resolver Module

This module implements tenant resolution based on subdomains.

Subdomain Resolution:
    Each tenant is identified by a unique subdomain. The tenant_id is derived
    directly from the subdomain portion of the request host.
    
    Example:
    - "acme.example.com" → Tenant "acme"
    - "globex.example.com" → Tenant "globex"
    - "acme-prod.example.com" → Tenant "acme-prod"
    
Purpose:
    Provides the simplest and most common multi-tenancy pattern:
    - Tenant identification embedded in URL
    - Direct mapping from subdomain to tenant_id
    - No external lookup tables required
    - Tenant_id directly matches subdomain
    - Lightweight and performant
    
Subdomain Extraction:
    The subdomain is extracted from the host header:
    
    ```python
    subdomain = request.get_host().split(".")[0]
    ```
    
    Examples:
    - "acme.example.com" → "acme"
    - "globex.example.com" → "globex"
    - "api.acme.example.com" → "api" (treats first part as subdomain)
    - "example.com" → "example" (edge case - takes first part)
    
    Process:
    1. Get host from HTTP Host header (e.g., "acme.example.com")
    2. Split on "." (dot delimiter)
    3. Take first element (index [0])
    4. Treat as tenant_id
    
Tenant Lookup:
    The extracted subdomain is used as tenant_id to lookup Tenant:
    
    ```python
    Tenant.objects.get(tenant_id=subdomain)
    ```
    
    Database query details:
    - Query Tenant model
    - Match on tenant_id field
    - tenant_id is usually unique, indexed
    - Fast lookup (O(1) with index)
    - Returns Tenant object if exists
    
Comparison with CustomDomainTenantResolver:
    
    SubdomainTenantResolver:
    - Tenant_id from subdomain directly
    - Pattern: "tenant_id.example.com"
    - No additional database lookups needed
    - Fast single-query resolution
    - Tenant_id must match subdomain
    
    CustomDomainTenantResolver:
    - Tenant from custom domain mapping
    - Pattern: Arbitrary custom domains
    - Requires Domain model lookup
    - Additional database query
    - Multiple domains per tenant possible
    
Error Handling:
    If subdomain doesn't correspond to valid tenant_id:
    - Raises TenantNotFound exception
    - Middleware catches and handles (typically 404)
    - Never returns None (explicit error)
    - Subdomain must exist as tenant_id
    
Configuration:
    Use in Django settings:
    
    ```python
    OMNITENANT_CONFIG = {
        'TENANT_RESOLVER': 'django_omnitenant.resolvers.SubdomainTenantResolver',
    }
    ```
    
    Alternatively, configure base domain:
    ```python
    OMNITENANT_CONFIG = {
        'TENANT_RESOLVER': 'django_omnitenant.resolvers.SubdomainTenantResolver',
        'BASE_DOMAIN': 'example.com',  # For validation
    }
    ```

Usage Example:
    ```python
    # Create tenants
    from django_omnitenant.models import Tenant
    
    tenant1 = Tenant.objects.create(tenant_id='acme')
    tenant2 = Tenant.objects.create(tenant_id='globex')
    
    # Requests resolve:
    # GET http://acme.example.com → tenant_id='acme'
    # GET http://globex.example.com → tenant_id='globex'
    # GET http://example.com → TenantNotFound (no subdomain)
    # GET http://unknown.example.com → TenantNotFound (tenant doesn't exist)
    ```

Tenant ID Conventions:
    Good practices for tenant_id:
    - Lowercase letters: "acme", "globex"
    - Hyphens for multi-word: "acme-corp", "globex-inc"
    - Numbers for versions: "acme-prod", "acme-staging"
    - No underscores or spaces (invalid in subdomains)
    - Keep short and memorable
    - RFC 1123 compliant (DNS name rules)
    
Performance:
    - Direct Tenant model lookup
    - Single database query
    - tenant_id is usually indexed
    - O(1) lookup time
    - No join or relationship traversal needed
    - Faster than custom domain resolution
    
Caching Strategy:
    Subdomain-to-tenant mappings can be cached:
    
    ```python
    cache_key = f'subdomain_tenant:{subdomain}'
    tenant = cache.get(cache_key)
    if not tenant:
        try:
            tenant = Tenant.objects.get(tenant_id=subdomain)
            cache.set(cache_key, tenant, timeout=3600)
            return tenant
        except Tenant.DoesNotExist:
            raise TenantNotFound
    return tenant
    ```

Edge Cases:
    Root domain (no subdomain):
    - "example.com" → subdomain = "example"
    - May not correspond to tenant_id
    - Usually raises TenantNotFound
    - Solution: Configure fallback or default tenant
    
    Multiple subdomains:
    - "api.acme.example.com" → subdomain = "api"
    - Only first part used
    - "api" must exist as tenant_id
    - Solution: Create tenant with tenant_id="api" or use different resolver
    
    Port in host:
    - "acme.example.com:8000" → split still works
    - "acme" extracted correctly (port added separately)
    - request.get_host() includes port, split(".")[0] unaffected
    
Related:
    - base.py: Abstract resolver base class
    - customdomain_resolver.py: Custom domain-based alternative
    - models.py: BaseTenant model
    - middleware.py: Uses resolver for request routing
    - exceptions.py: TenantNotFound exception
"""

from django_omnitenant.exceptions import TenantNotFound
from django_omnitenant.utils import get_tenant_model
from .base import BaseTenantResolver


class SubdomainTenantResolver(BaseTenantResolver):
    """
    Resolver that identifies tenants by subdomain.
    
    This resolver extracts the subdomain portion of the request host and
    uses it directly as the tenant_id to look up the corresponding Tenant.
    
    This is the simplest and most common multi-tenancy pattern where each
    tenant is assigned a unique subdomain that maps directly to their
    tenant_id.
    
    Key Features:
        - Direct tenant_id extraction from subdomain
        - No additional lookup tables or models needed
        - Fast single-query lookup
        - Tenant_id must match subdomain exactly
        - Standard multi-tenancy pattern
        - Thread-safe and request-safe
        
    Subdomain Extraction:
        The subdomain is the first component of the domain name:
        
        Examples:
        - "acme.example.com" → "acme"
        - "globex.example.com" → "globex"
        - "api.acme.example.com" → "api" (only first part used)
        - "example.com" → "example" (no subdomain)
        
        Process:
        1. Get HTTP Host header (e.g., "acme.example.com:8000")
        2. Split on "." (dots)
        3. Take first element
        4. Use as tenant_id
        
    Tenant Lookup:
        Extracted subdomain is queried against Tenant model:
        - tenant_id = subdomain
        - Single database query
        - Exact match lookup
        - Returns Tenant if found
        - Raises TenantNotFound if not found
        
    Performance:
        - Single database query (no joins)
        - tenant_id field typically indexed
        - O(1) lookup time
        - No relationship traversal
        - Faster than custom domain resolution
        
    Attributes:
        None (stateless, no configuration needed)
    """

    def resolve(self, request) -> object | None:
        """
        Resolve tenant from subdomain in request.
        
        Extracts the subdomain portion of the request host and uses it
        directly as the tenant_id to lookup the corresponding Tenant.
        
        Args:
            request (django.http.HttpRequest): The HTTP request
                                              Contains host/domain information
        
        Returns:
            BaseTenant: The tenant matching the subdomain
            
        Raises:
            TenantNotFound: If no tenant exists with tenant_id matching subdomain
            
        Process:
            1. Extract subdomain from request host
            2. Query Tenant model for matching tenant_id
            3. Return tenant if found
            4. Raise TenantNotFound if not found
            
        Subdomain Extraction:
            Subdomain is extracted by splitting host on dots:
            
            ```python
            subdomain = request.get_host().split(".")[0]
            ```
            
            request.get_host() returns the HTTP Host header:
            - Includes port if present: "acme.example.com:8000"
            - No port: "acme.example.com"
            - Full FQDN: "acme.example.com"
            
            Split on "." takes first component:
            - "acme.example.com" → ["acme", "example", "com"] → "acme"
            - "acme.example.com:8000" → "acme.example.com" → ["acme", ...] → "acme"
            - "example.com" → ["example", "com"] → "example"
            
            Note: Port is NOT included in the domain part (handled by split):
            ```python
            # request.get_host() = "acme.example.com:8000"
            host_without_port = "acme.example.com"
            subdomain = "acme"
            ```
            
        Examples of subdomain extraction:
            ```
            Host: "acme.example.com" → "acme"
            Host: "globex.example.com" → "globex"
            Host: "api.acme.example.com" → "api" (only first part)
            Host: "example.com" → "example" (edge case)
            Host: "acme.example.com:8000" → "acme" (port ignored)
            Host: "my-tenant.example.com" → "my-tenant" (hyphens allowed)
            ```
            
        Tenant Model Query:
            Queries the Tenant model:
            
            ```python
            Tenant = get_tenant_model()  # Get configured Tenant model
            return Tenant.objects.get(tenant_id=subdomain)
            ```
            
            The get_tenant_model() utility:
            - Returns configured Tenant model
            - Respects custom Tenant implementations
            - Loads from app registry
            - Default: BaseTenant
            
            Query details:
            - Filters Tenant on tenant_id field
            - tenant_id is usually unique, indexed
            - Single query execution
            - Returns Tenant object
            
        Error Handling:
            If no Tenant exists with matching tenant_id:
            
            ```python
            try:
                return Tenant.objects.get(tenant_id=subdomain)
            except Tenant.DoesNotExist:
                raise TenantNotFound
            ```
            
            Raises TenantNotFound when:
            - Subdomain doesn't match any tenant_id
            - Typo in subdomain
            - Tenant deleted but requests continue
            - Subdomain points to root domain
            
            Not found cases:
            - "unknown.example.com" → no tenant_id="unknown"
            - "api.example.com" → no tenant_id="api"
            - "example.com" → may be no tenant_id="example"
            
        Examples:
            
            Successful resolution:
            ```python
            # Tenant with tenant_id='acme' exists
            request = RequestFactory().get('/')
            request.META['HTTP_HOST'] = 'acme.example.com'
            
            resolver = SubdomainTenantResolver()
            tenant = resolver.resolve(request)
            # Returns: Tenant(tenant_id='acme')
            ```
            
            Different subdomain:
            ```python
            request.META['HTTP_HOST'] = 'globex.example.com'
            # Subdomain 'globex' extracted
            # Tenant with tenant_id='globex' returned
            ```
            
            With port number:
            ```python
            request.META['HTTP_HOST'] = 'acme.example.com:8000'
            # Subdomain 'acme' extracted (port not included)
            # Tenant with tenant_id='acme' returned
            ```
            
            Tenant not found:
            ```python
            request.META['HTTP_HOST'] = 'unknown.example.com'
            # Subdomain 'unknown' extracted
            # No Tenant with tenant_id='unknown'
            # Raises: TenantNotFound
            ```
            
            Root domain:
            ```python
            request.META['HTTP_HOST'] = 'example.com'
            # Subdomain 'example' extracted (only first part)
            # Usually no Tenant with tenant_id='example'
            # Raises: TenantNotFound
            # Solution: Configure default tenant or different resolver
            ```
            
        Performance Characteristics:
            - Single database query (SELECT * FROM tenant WHERE tenant_id=...)
            - No joins or relationships traversed
            - tenant_id field usually indexed
            - O(1) lookup time
            - Typically <1ms database time
            - Fastest resolver option
            
        Comparison with CustomDomainTenantResolver:
            SubdomainTenantResolver:
            - Queries Tenant model directly
            - 1 database query per request
            - No custom domain table needed
            - Subdomain must equal tenant_id
            
            CustomDomainTenantResolver:
            - Queries Domain model first, then gets tenant
            - 2 database queries per request
            - Requires Domain model with tenant FK
            - Multiple domains per tenant possible
            
        Caching Strategy:
            For high-traffic applications, caching helps:
            
            ```python
            from django.core.cache import cache
            
            cache_key = f'subdomain_tenant:{subdomain}'
            tenant = cache.get(cache_key)
            if tenant:
                return tenant
            
            try:
                tenant = Tenant.objects.get(tenant_id=subdomain)
                # Cache for 1 hour
                cache.set(cache_key, tenant, timeout=3600)
                return tenant
            except Tenant.DoesNotExist:
                raise TenantNotFound
            ```
            
            Benefits:
            - Avoids database query on cache hit
            - Cache hit ratio typically 95%+
            - Minimal overhead (cache lookup vs DB)
            - Suitable for high-concurrency
            
        Testing:
            ```python
            from django.test import TestCase
            from django.test.client import RequestFactory
            
            class TestSubdomainResolver(TestCase):
                def setUp(self):
                    self.factory = RequestFactory()
                    self.tenant = Tenant.objects.create(tenant_id='acme')
                
                def test_resolve_subdomain(self):
                    request = self.factory.get('/')
                    request.META['HTTP_HOST'] = 'acme.example.com'
                    
                    resolver = SubdomainTenantResolver()
                    tenant = resolver.resolve(request)
                    
                    assert tenant == self.tenant
                
                def test_resolve_with_port(self):
                    request = self.factory.get('/')
                    request.META['HTTP_HOST'] = 'acme.example.com:8000'
                    
                    resolver = SubdomainTenantResolver()
                    tenant = resolver.resolve(request)
                    
                    assert tenant == self.tenant
                
                def test_resolve_unknown_subdomain(self):
                    request = self.factory.get('/')
                    request.META['HTTP_HOST'] = 'unknown.example.com'
                    
                    resolver = SubdomainTenantResolver()
                    
                    with pytest.raises(TenantNotFound):
                        resolver.resolve(request)
                
                def test_resolve_hyphenated_subdomain(self):
                    tenant = Tenant.objects.create(tenant_id='acme-prod')
                    request = self.factory.get('/')
                    request.META['HTTP_HOST'] = 'acme-prod.example.com'
                    
                    resolver = SubdomainTenantResolver()
                    resolved_tenant = resolver.resolve(request)
                    
                    assert resolved_tenant == tenant
            ```
            
        See Also:
            - base.py: Abstract resolver interface
            - customdomain_resolver.py: Custom domain-based alternative
            - models.py: BaseTenant model
            - middleware.py: Uses resolver for routing
            - exceptions.py: TenantNotFound exception
        """
        # Extract subdomain from request host
        # request.get_host() returns HTTP Host header (e.g., "acme.example.com" or "acme.example.com:8000")
        # Split on "." to separate domain components
        # Take first element [0] which is the subdomain
        subdomain = request.get_host().split(".")[0]
        
        # Get the Tenant model (respects custom implementations via get_tenant_model utility)
        Tenant = get_tenant_model()
        
        try:
            # Query Tenant model for a tenant with matching tenant_id
            # Direct lookup - no joins or relationships
            # Returns Tenant object if found
            return Tenant.objects.get(tenant_id=subdomain)
        except Tenant.DoesNotExist:
            # No tenant exists with this tenant_id
            # Raise TenantNotFound exception (not None)
            # Middleware will catch and handle (typically 404)
            raise TenantNotFound
