"""
Custom Domain Tenant Resolver Module

This module implements tenant resolution based on custom domain names.

Custom Domain Resolution:
    Each tenant can have one or more custom domains. This resolver maps incoming
    requests from custom domains to their corresponding tenants.
    
    Example:
    - Domain "acme.com" → Tenant "acme"
    - Domain "globex.io" → Tenant "globex"
    - Domain "acmecorp.co.uk" → Tenant "acme"
    
Purpose:
    Allows tenants to use their own branded domains instead of subdomains:
    - "acme.com" instead of "acme.example.com"
    - Branded experience for each tenant
    - Custom TLDs and domain extensions
    - Multiple domains per tenant (acme.com, acme.io, acmecorp.com, etc.)
    
Domain Model:
    The BaseDomain model stores domain-to-tenant mappings:
    
    ```python
    class BaseDomain(models.Model):
        domain = models.CharField(max_length=253, unique=True)
        is_primary = models.BooleanField(default=True)
        tenant = models.ForeignKey(BaseTenant, on_delete=models.CASCADE)
        created_at = models.DateTimeField(auto_now_add=True)
    ```
    
    Example data:
    - Domain: "acme.com" → Tenant: "acme"
    - Domain: "acme.io" → Tenant: "acme"
    - Domain: "www.acme.com" → Tenant: "acme" (handled by resolver)
    
Resolution Process:
    1. Extract domain from request host (e.g., "acme.com" from "acme.com:8000")
    2. Remove "www." prefix if present (normalize)
    3. Query Domain model for matching domain
    4. Return associated tenant if found
    5. Raise DomainNotFound if no matching domain
    
Host Normalization:
    The resolver normalizes the requested host:
    
    Input host examples:
    - "acme.com" → "acme.com"
    - "www.acme.com" → "acme.com"
    - "acme.com:8000" → "acme.com" (port removed)
    - "www.acme.com:8000" → "acme.com" (port and www removed)
    
    Normalization rules:
    1. Remove port number (split on ":", take first part)
    2. Remove "www." prefix if present
    3. Domain lookup on normalized name
    
Master Database Access:
    Domain queries always use the master/public database:
    
    ```python
    with TenantContext.use_master_db():
        Domain.objects.get(domain=host_name)
    ```
    
    This ensures:
    - Consistent domain lookups across all tenants
    - Domains stored in shared/public database
    - Not affected by current tenant context
    - Correct tenant is found regardless of prior context
    
Error Handling:
    If domain doesn't exist:
    - Raises DomainNotFound exception
    - Middleware catches and handles (typically 404)
    - Never returns None (explicit error vs. no match)
    
Comparison with SubdomainTenantResolver:
    
    SubdomainTenantResolver:
    - Tenant ID from subdomain directly
    - Pattern: "tenant_id.example.com"
    - Tenant must exist with matching tenant_id
    - Query Tenant model
    
    CustomDomainTenantResolver:
    - Tenant from custom domain mapping
    - Pattern: Arbitrary custom domains
    - Domain must exist in Domain model
    - Query Domain model, then get tenant
    
Performance:
    - Domain lookup is single database query
    - Can be cached via database query caching
    - Should use select_related('tenant') for optimization
    - Master database is shared, fast lookup
    
Caching Strategy:
    Domain-to-tenant mappings can be cached:
    
    ```python
    from django.core.cache import cache
    
    cache_key = f'domain_tenant:{host_name}'
    tenant = cache.get(cache_key)
    if not tenant:
        with TenantContext.use_master_db():
            domain = Domain.objects.select_related('tenant').get(domain=host_name)
            tenant = domain.tenant
        cache.set(cache_key, tenant, timeout=3600)
    return tenant
    ```
    
Configuration:
    Use in Django settings:
    
    ```python
    OMNITENANT_CONFIG = {
        'TENANT_RESOLVER': 'django_omnitenant.resolvers.CustomDomainTenantResolver',
    }
    ```

Usage Example:
    ```python
    # Create domain mapping
    from django_omnitenant.models import Tenant
    from myapp.models import Domain
    
    tenant = Tenant.objects.create(tenant_id='acme')
    Domain.objects.create(
        domain='acme.com',
        is_primary=True,
        tenant=tenant
    )
    Domain.objects.create(
        domain='acme.io',
        is_primary=False,
        tenant=tenant
    )
    
    # Request to acme.com resolves to acme tenant
    # Request to acme.io also resolves to acme tenant
    # Request to www.acme.com normalized to acme.com, resolves to acme tenant
    ```

Related:
    - base.py: Abstract resolver base class
    - subdomain_resolver.py: Subdomain-based resolution
    - models.py: BaseDomain and BaseTenant models
    - middleware.py: Uses resolver for request routing
    - exceptions.py: DomainNotFound exception
"""

from django_omnitenant.exceptions import DomainNotFound
from django_omnitenant.models import BaseDomain
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_domain_model

from .base import BaseTenantResolver


class CustomDomainTenantResolver(BaseTenantResolver):
    """
    Resolver that identifies tenants by custom domain names.
    
    This resolver maps custom domain names to tenants via the Domain model.
    Each tenant can have multiple custom domains associated with it.
    
    Custom domains allow branded experiences where each tenant uses their
    own domain (e.g., "acme.com" instead of "acme.example.com").
    
    Key Features:
        - Maps custom domains to tenants
        - Normalizes hosts (removes port, www prefix)
        - Queries master/public database for consistency
        - Raises DomainNotFound if domain doesn't exist
        - Supports multiple domains per tenant
        - Handles port numbers in requests
        
    Domain-to-Tenant Mapping:
        Domains are stored in the Domain model:
        - domain: Custom domain name (e.g., "acme.com")
        - tenant: Foreign key to Tenant
        - is_primary: Whether this is primary domain
        - Multiple domains can point to same tenant
        
    Host Normalization:
        Incoming hosts are normalized:
        1. Extract hostname (remove port)
        2. Remove "www." prefix
        
        Examples:
        - "acme.com" → "acme.com"
        - "www.acme.com" → "acme.com"
        - "acme.com:8000" → "acme.com"
        - "www.acme.com:8000" → "acme.com"
        
    Master Database:
        Domain lookups always use master database:
        - Ensures consistent domain resolution
        - Not affected by current tenant context
        - Domains are shared across all tenants
        - Master database holds authoritative mappings
        
    Error Handling:
        Raises DomainNotFound if domain doesn't exist:
        - Explicit exception (not None)
        - Middleware catches and handles
        - Typically results in 404 Not Found
        - Never returns None
        
    Performance:
        - Single database query per request
        - Master database lookup
        - Can be cached in application/HTTP cache
        - Use select_related for tenant optimization
        
    Attributes:
        None (stateless, configuration via Domain model)
    """

    def resolve(self, request) -> object | None:
        """
        Resolve tenant from custom domain in request.
        
        Examines the request host/domain and looks up the corresponding
        tenant via the Domain model.
        
        Args:
            request (django.http.HttpRequest): The HTTP request
                                              Contains host/domain information
        
        Returns:
            BaseTenant: The tenant associated with the custom domain
            
        Raises:
            DomainNotFound: If no Domain exists for the host
            
        Process:
            1. Extract hostname from request.get_host()
            2. Remove port number if present (split on ":")
            3. Remove "www." prefix if present
            4. Query Domain model in master database
            5. Return associated tenant
            6. Raise DomainNotFound if not found
            
        Host Extraction:
            request.get_host() returns the HTTP Host header:
            - Includes port if present: "acme.com:8000"
            - Includes www if requested: "www.acme.com"
            - Lowercased by some servers, not others
            
            Examples:
            ```
            request.get_host() = "acme.com"
            request.get_host() = "www.acme.com"
            request.get_host() = "acme.com:8000"
            request.get_host() = "www.acme.com:8000"
            ```
            
        Port Removal:
            Port numbers are split off using:
            ```python
            host_name = request.get_host().split(":")[0]
            ```
            
            This extracts only the hostname part:
            - "acme.com:8000" → "acme.com"
            - "acme.com" → "acme.com" (no port)
            - "www.acme.com:8080" → "www.acme.com"
            
        WWW Prefix Removal:
            The "www." prefix is removed if present:
            ```python
            if host_name.startswith("www."):
                host_name = host_name[4:]  # Remove first 4 chars
            ```
            
            This normalizes common domain variants:
            - "www.acme.com" → "acme.com"
            - "acme.com" → "acme.com" (unchanged)
            - "www.www.acme.com" → "www.acme.com" (only first www removed)
            
            Rationale:
            - Domain model stores "acme.com"
            - Both "acme.com" and "www.acme.com" should work
            - Normalization ensures consistent lookups
            
        Domain Model Query:
            Queries the Domain model:
            
            ```python
            Domain = get_domain_model()
            domain = Domain.objects.get(domain=host_name)
            return domain.tenant
            ```
            
            The get_domain_model() utility returns the configured Domain model:
            - Respects custom Domain implementations
            - Loads from app registry
            - Default: BaseDomain
            
        Master Database Access:
            Domain query uses master database:
            
            ```python
            with TenantContext.use_master_db():
                return Domain.objects.get(domain=host_name).tenant
            ```
            
            Benefits:
            - Consistent resolution regardless of current tenant
            - Domains stored in shared/public database
            - Not affected by tenant context switching
            - Thread-safe and request-safe
            
            How it works:
            - TenantContext.use_master_db() is context manager
            - Temporarily switches context to master database
            - All database queries in context use master DB
            - Restores previous context on exit
            
        Error Handling:
            If Domain doesn't exist:
            
            ```python
            except Domain.DoesNotExist:
                raise DomainNotFound
            ```
            
            Raises DomainNotFound exception:
            - Explicit error (not None)
            - Middleware catches this exception
            - Typically results in HTTP 404
            - Application can handle domain mismatches
            
            Not found cases:
            - Typo in domain name
            - Unknown custom domain
            - Domain not yet registered
            - Domain deleted
            
        Examples:
            
            Successful resolution:
            ```python
            # Domain "acme.com" maps to tenant "acme"
            request = RequestFactory().get('/')
            request.META['HTTP_HOST'] = 'acme.com'
            
            resolver = CustomDomainTenantResolver()
            tenant = resolver.resolve(request)
            # Returns: Tenant(tenant_id='acme')
            ```
            
            With www prefix:
            ```python
            request.META['HTTP_HOST'] = 'www.acme.com'
            # Normalized to 'acme.com'
            # Returns: Tenant(tenant_id='acme')
            ```
            
            With port:
            ```python
            request.META['HTTP_HOST'] = 'acme.com:8000'
            # Port removed → 'acme.com'
            # Returns: Tenant(tenant_id='acme')
            ```
            
            Domain not found:
            ```python
            request.META['HTTP_HOST'] = 'unknown.com'
            # No domain for unknown.com
            # Raises: DomainNotFound
            ```
            
        Performance Considerations:
            - Single database query to Domain table
            - Can use select_related('tenant') for optimization
            - Master database query (not tenant database)
            - Should cache results for high traffic
            
        Caching Example:
            ```python
            def resolve(self, request):
                host_name = request.get_host().split(":")[0]
                if host_name.startswith("www."):
                    host_name = host_name[4:]
                
                # Try cache first
                cache_key = f'domain_tenant:{host_name}'
                tenant = cache.get(cache_key)
                if tenant:
                    return tenant
                
                # Query database
                Domain = get_domain_model()
                try:
                    with TenantContext.use_master_db():
                        domain = Domain.objects.select_related(
                            'tenant'
                        ).get(domain=host_name)
                        tenant = domain.tenant
                    
                    # Cache for 1 hour
                    cache.set(cache_key, tenant, timeout=3600)
                    return tenant
                except Domain.DoesNotExist:
                    raise DomainNotFound
            ```
            
        Testing:
            ```python
            from django.test import TestCase
            from django.test.client import RequestFactory
            
            class TestCustomDomainResolver(TestCase):
                def setUp(self):
                    self.factory = RequestFactory()
                    self.tenant = Tenant.objects.create(tenant_id='acme')
                    self.domain = Domain.objects.create(
                        domain='acme.com',
                        tenant=self.tenant
                    )
                
                def test_resolve_custom_domain(self):
                    request = self.factory.get('/')
                    request.META['HTTP_HOST'] = 'acme.com'
                    
                    resolver = CustomDomainTenantResolver()
                    tenant = resolver.resolve(request)
                    
                    assert tenant == self.tenant
                
                def test_resolve_www_subdomain(self):
                    request = self.factory.get('/')
                    request.META['HTTP_HOST'] = 'www.acme.com'
                    
                    resolver = CustomDomainTenantResolver()
                    tenant = resolver.resolve(request)
                    
                    assert tenant == self.tenant
                
                def test_resolve_with_port(self):
                    request = self.factory.get('/')
                    request.META['HTTP_HOST'] = 'acme.com:8000'
                    
                    resolver = CustomDomainTenantResolver()
                    tenant = resolver.resolve(request)
                    
                    assert tenant == self.tenant
                
                def test_resolve_unknown_domain(self):
                    request = self.factory.get('/')
                    request.META['HTTP_HOST'] = 'unknown.com'
                    
                    resolver = CustomDomainTenantResolver()
                    
                    with pytest.raises(DomainNotFound):
                        resolver.resolve(request)
            ```
            
        See Also:
            - base.py: Abstract resolver interface
            - subdomain_resolver.py: Subdomain-based alternative
            - models.py: BaseDomain and BaseTenant models
            - middleware.py: Uses resolver for routing
            - exceptions.py: DomainNotFound exception
            - tenant_context.py: use_master_db() context manager
        """
        # Extract hostname from request
        # request.get_host() returns HTTP Host header (may include port)
        # Split on ":" to remove port number
        host_name = request.get_host().split(":")[0]
        
        # Remove "www." prefix if present
        # Normalizes common domain variants
        # "www.acme.com" → "acme.com"
        # "acme.com" → "acme.com" (unchanged)
        if host_name.startswith("www."):
            host_name = host_name[4:]

        # Get the Domain model (respects custom implementations)
        Domain: BaseDomain = get_domain_model()  # type: ignore
        
        try:
            # Query Domain model in master/public database
            # Ensures consistent resolution regardless of current tenant context
            # Returns the tenant associated with this domain
            with TenantContext.use_master_db():
                return Domain.objects.get(domain=host_name).tenant
        except Domain.DoesNotExist:
            # No domain exists for this hostname
            # Raise DomainNotFound exception (not None)
            # Middleware will catch and handle (typically 404)
            raise DomainNotFound
