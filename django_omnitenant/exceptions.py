"""
Custom Exception Classes for django-omnitenant

This module defines custom exceptions used throughout the django-omnitenant package
for handling multi-tenancy-related errors. These exceptions are raised when tenant
or domain resolution fails or when required configuration is missing.

Exceptions in this module:
    - TenantNotFound: Raised when a requested tenant cannot be located
    - DomainNotFound: Raised when a requested domain cannot be located

Usage:
    from django_omnitenant.exceptions import TenantNotFound, DomainNotFound
    
    try:
        tenant = get_tenant(tenant_id)
    except TenantNotFound:
        # Handle missing tenant
        logger.warning(f"Tenant {tenant_id} not found")
"""


class TenantNotFound(Exception):
    """
    Exception raised when a tenant cannot be found.
    
    This exception is raised when:
    - A tenant lookup fails (by ID, slug, or other identifier)
    - A tenant resolver cannot determine the current tenant from a request
    - Attempting to access a tenant that doesn't exist in the database
    - Tenant context is required but no valid tenant is available
    
    Attributes:
        message (str): Description of why the tenant was not found
        
    Examples:
        Raising the exception with a custom message:
        
        ```python
        from django_omnitenant.exceptions import TenantNotFound
        
        def get_tenant_by_id(tenant_id):
            try:
                return Tenant.objects.get(id=tenant_id)
            except Tenant.DoesNotExist:
                raise TenantNotFound(f"Tenant with id {tenant_id} not found")
        ```
        
        Handling the exception:
        
        ```python
        from django_omnitenant.exceptions import TenantNotFound
        
        try:
            tenant = resolve_tenant_from_request(request)
        except TenantNotFound:
            return error_response("Unable to determine current tenant")
        ```
        
    Related:
        - DomainNotFound: Exception for missing domain
        - Tenant Model: The model that represents a tenant
        - Resolvers: Components that determine tenant from request
        
    Note:
        This exception inherits from Python's base Exception class and should be
        caught specifically when handling tenant resolution failures.
    """
    pass


class DomainNotFound(Exception):
    """
    Exception raised when a domain cannot be found.
    
    This exception is raised when:
    - A domain lookup fails (by name or URL)
    - A custom domain cannot be resolved to a tenant
    - A domain resolver cannot determine the domain from a request
    - Attempting to access a domain that doesn't exist in the database
    - Domain validation fails during tenant resolution
    
    Attributes:
        message (str): Description of why the domain was not found
        
    Examples:
        Raising the exception with a custom message:
        
        ```python
        from django_omnitenant.exceptions import DomainNotFound
        
        def get_domain_by_name(domain_name):
            try:
                return Domain.objects.get(name=domain_name)
            except Domain.DoesNotExist:
                raise DomainNotFound(f"Domain {domain_name} not found")
        ```
        
        Handling the exception:
        
        ```python
        from django_omnitenant.exceptions import DomainNotFound
        
        try:
            domain = resolve_domain_from_host(request.get_host())
        except DomainNotFound:
            return error_response("Invalid domain")
        ```
        
    Related:
        - TenantNotFound: Exception for missing tenant
        - Domain Model: The model that represents a domain
        - Custom Domain Resolver: Component for resolving custom domains
        - Subdomain Resolver: Component for resolving subdomains
        
    Note:
        This exception inherits from Python's base Exception class and should be
        caught specifically when handling domain resolution failures.
    """
    pass
