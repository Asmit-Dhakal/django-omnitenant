# API Reference

Welcome to the **django-omnitenant** API Reference. This section provides comprehensive documentation for all modules, classes, functions, and management commands.

## Overview

django-omnitenant is organized into several key components:

- **Core**: Central functionality for tenant management, context, and configuration
- **Models**: Tenant and domain models with query managers
- **Backends**: Isolation strategy implementations (database, schema, cache)
- **Resolvers**: Tenant resolution strategies from HTTP requests
- **Admin**: Django admin integration with tenant awareness
- **Management Commands**: CLI tools for tenant operations
- **Patches**: Integration patches for Celery and Cache frameworks

## Quick Navigation

### Core Components

The foundation of django-omnitenant:

- [`Tenant Context`](core/tenant_context.md) - Thread-safe tenant context management
- [`Middleware`](core/middleware.md) - HTTP request tenant resolution middleware
- [`Utils`](core/utils.md) - Utility functions for tenant and backend access
- [`Configuration`](core/conf.md) - Settings and configuration management
- [`Exceptions`](core/exceptions.md) - Custom exceptions for error handling
- [`Signals`](core/signals.md) - Django signals for tenant lifecycle events
- [`Validators`](core/validators.md) - Validation functions for tenant data
- [`Constants`](core/constants.md) - Configuration constants
- [`Bootstrap`](core/bootstrap.md) - Application initialization

### Data Models

Define and manage tenant data:

- [`Models`](models.md) - `BaseTenant`, `BaseDomain`, and query managers

### Isolation Backends

Implement different isolation strategies:

- [`Base Backend`](backends/base.md) - Abstract backend interface
- [`Database Backend`](backends/database_backend.md) - Database-per-tenant isolation
- [`Schema Backend`](backends/schema_backend.md) - PostgreSQL schema isolation
- [`Cache Backend`](backends/cache_backend.md) - Cache-based isolation
- [`PostgreSQL Backend`](backends/postgresql/base.md) - PostgreSQL-specific implementation

### Tenant Resolution

Extract tenant information from requests:

- [`Base Resolver`](resolvers/base.md) - Abstract resolver interface
- [`Custom Domain Resolver`](resolvers/customdomain_resolver.md) - Resolve by custom domain
- [`Subdomain Resolver`](resolvers/subdomain_resolver.md) - Resolve by subdomain

### Admin Interface

Django admin integration:

- [`Admin`](admin.md) - Tenant-aware admin mixins and utilities

### Framework Integration

Patches for external frameworks:

- [`Cache Patch`](patches/cache.md) - Tenant-scoped caching
- [`Celery Patch`](patches/celery.md) - Tenant-aware task execution

### Management Commands

Command-line tools for tenant management:

- [`Create Tenant`](management_commands/createtenant.md) - Create new tenants
- [`Create Tenant Superuser`](management_commands/createtenantsuperuser.md) - Create admin users
- [`Migrate Tenant`](management_commands/migratetenant.md) - Run migrations for specific tenant
- [`Migrate All Tenants`](management_commands/migratealltenants.md) - Migrate all tenants
- [`Shell`](management_commands/shell.md) - Interactive shell with tenant context
- [`Show Tenants`](management_commands/showtenants.md) - List and export tenant information

## Architecture

### Isolation Strategies

Choose how to isolate tenant data:

**Database-per-Tenant**
- Each tenant has a separate database
- Complete data isolation
- See: [`Database Backend`](backends/database_backend.md)

**Schema-per-Tenant**
- PostgreSQL schemas within shared database
- Good balance of isolation and resources
- See: [`Schema Backend`](backends/schema_backend.md)

**Cache Isolation**
- Tenant-scoped cache keys
- Lightweight isolation
- See: [`Cache Backend`](backends/cache_backend.md)

### Request Flow

1. **HTTP Request** → [`Middleware`](core/middleware.md) receives request
2. **Tenant Resolution** → [`Resolver`](resolvers/base.md) extracts tenant from request
3. **Context Activation** → [`Tenant Context`](core/tenant_context.md) sets current tenant
4. **Database Routing** → Database router directs queries to correct database/schema
5. **Response** → Django processes request with tenant context active

## Common Tasks

### Access Current Tenant

```python
from django_omnitenant.tenant_context import TenantContext

tenant = TenantContext.get_tenant()
```

See: [`Tenant Context`](core/tenant_context.md)

### Get Configured Models

```python
from django_omnitenant.utils import get_tenant_model, get_domain_model

Tenant = get_tenant_model()
Domain = get_domain_model()
```

See: [`Utils`](core/utils.md)

### Create Tenant Programmatically

```python
from django_omnitenant.utils import get_tenant_model, get_tenant_backend

Tenant = get_tenant_model()
tenant = Tenant.objects.create(
    tenant_id='acme',
    name='ACME Corporation'
)

backend = get_tenant_backend(tenant)
backend.create(run_migrations=True)
```

See: [`Management Commands`](#management-commands)

### Switch Tenant Context

```python
from django_omnitenant.tenant_context import TenantContext

with TenantContext.use_tenant(tenant):
    # Query in tenant context
    items = MyModel.objects.all()
```

See: [`Tenant Context`](core/tenant_context.md)

### Query Tenant Data

```python
from myapp.models import MyModel

# Automatically scoped to current tenant
items = MyModel.objects.all()
item = MyModel.objects.get(id=1)
```

See: [`Models`](models.md)

### Create Signal Handlers

```python
from django.dispatch import receiver
from django_omnitenant.signals import tenant_created

@receiver(tenant_created)
def setup_tenant(sender, tenant, **kwargs):
    # Initialize tenant
    pass
```

See: [`Signals`](core/signals.md)

### Integrate with Celery

```python
from celery import shared_task
from django_omnitenant.patches.celery import TenantAwareTask

@shared_task(base=TenantAwareTask)
def process_tenant_data(tenant_id):
    # Task runs in tenant context
    pass
```

See: [`Celery Patch`](patches/celery.md)

## Module Organization

### Core Module (`django_omnitenant`)

Central functionality:

```
django_omnitenant/
├── tenant_context.py      # TenantContext class
├── middleware.py          # TenantMiddleware
├── models.py              # BaseTenant, BaseDomain
├── utils.py               # Utility functions
├── conf.py                # Settings wrapper
├── signals.py             # Django signals
├── exceptions.py          # Custom exceptions
├── validators.py          # Validation functions
├── constants.py           # Constants
├── bootstrap.py           # App initialization
├── admin.py               # Admin mixins
├── routers.py             # Database router
├── backends/              # Isolation backends
├── resolvers/             # Tenant resolvers
├── patches/               # Framework patches
├── management/            # Management commands
└── migrations/            # Database migrations
```

### Backends

Isolation strategy implementations:

```
backends/
├── base.py                # BaseTenantBackend
├── database_backend.py    # DatabaseTenantBackend
├── schema_backend.py      # SchemaTenantBackend
├── cache_backend.py       # CacheTenantBackend
└── postgresql/
    └── base.py            # PostgreSQL-specific implementation
```

### Resolvers

Tenant identification strategies:

```
resolvers/
├── base.py                # BaseTenantResolver
├── customdomain_resolver.py     # CustomDomainTenantResolver
└── subdomain_resolver.py  # SubdomainTenantResolver
```

### Management Commands

CLI tools:

```
management/commands/
├── createtenant.py        # Create tenant
├── createtenantsuperuser.py     # Create superuser
├── migratetenant.py       # Migrate single tenant
├── migratealltenants.py   # Migrate all tenants
├── shell.py               # Interactive shell
└── showtenants.py         # List tenants
```

### Patches

External framework integration:

```
patches/
├── cache.py               # Cache integration
└── celery.py              # Celery integration
```

## Class Hierarchy

### Backend Hierarchy

```
BaseTenantBackend
├── DatabaseTenantBackend
├── SchemaTenantBackend
└── CacheTenantBackend
```

### Resolver Hierarchy

```
BaseTenantResolver
├── CustomDomainTenantResolver
└── SubdomainTenantResolver
```

### Model Hierarchy

```
models.Model
├── BaseTenant (abstract)
│   └── YourTenant
├── BaseDomain (abstract)
│   └── YourDomain
└── TenantQuerySetManager (custom manager)
```

## Key Concepts

### Tenant Context

Thread-safe context variable for storing current tenant. Used throughout the application to scope queries and operations.

**Methods:**
- `get_tenant()` - Get current tenant
- `use_tenant(tenant)` - Switch to tenant context
- `use_master_db()` - Access master database
- `use_schema(schema_name)` - Access specific schema

**See:** [`Tenant Context`](core/tenant_context.md)

### Database Router

Routes ORM queries to correct database/schema based on current tenant context.

**See:** `routers.py` in main module

### Signals

Django signals emitted at key tenant lifecycle events:

- `tenant_created` - After tenant creation
- `tenant_migrated` - After migrations complete
- `tenant_deleted` - After tenant deletion

**See:** [`Signals`](core/signals.md)

### Tenant Backends

Abstractions for different isolation strategies. Each backend implements:

- `create()` - Create tenant resources
- `activate()` - Activate for current context
- `deactivate()` - Deactivate context
- `delete()` - Delete tenant resources

**See:** [`Backends`](#isolation-backends)

### Tenant Resolvers

Strategies to extract tenant from HTTP request. Implements:

- `resolve(request)` - Extract and return tenant

**See:** [`Resolvers`](#tenant-resolution)

## Configuration

Key configuration settings:

```python
OMNITENANT_CONFIG = {
    'TENANT_MODEL': 'myapp.Tenant',
    'DOMAIN_MODEL': 'myapp.Domain',
    'PUBLIC_HOST': 'example.com',
    'PUBLIC_TENANT_NAME': 'public',
    'MASTER_TENANT_NAME': 'master',
    'TENANT_RESOLVER': 'django_omnitenant.resolvers.CustomDomainTenantResolver',
}
```

**See:** [`Configuration`](core/conf.md)

## Common Patterns

### Multi-Tenant Queries

```python
# Automatically scoped to current tenant
from myapp.models import Project

projects = Project.objects.all()  # Tenant-filtered
active = Project.objects.filter(status='active')
```

### Cross-Tenant Operations

```python
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_tenant_model

Tenant = get_tenant_model()
for tenant in Tenant.objects.all():
    with TenantContext.use_tenant(tenant):
        # Operations in each tenant's context
        pass
```

### Custom Resolvers

```python
from django_omnitenant.resolvers.base import BaseTenantResolver

class CustomResolver(BaseTenantResolver):
    def resolve(self, request):
        # Extract tenant from request
        pass
```

## Error Handling

Key exceptions:

- `TenantNotFound` - Tenant not found during resolution
- `DomainNotFound` - Domain not found
- `ImproperlyConfigured` - Configuration error

**See:** [`Exceptions`](core/exceptions.md)

## Performance Considerations

- Use tenant context managers for batch operations
- Enable connection pooling in database settings
- Leverage cache isolation for frequently accessed data
- Use `select_related()` and `prefetch_related()` for efficient queries

## Security Best Practices

- Always verify tenant context in views
- Use `TenantRestrictAdminMixin` for admin protection
- Store database credentials securely
- Validate tenant access in signal handlers
- Implement rate limiting per tenant

## Links

- **Installation:** [Installation Guide](../installation.md)
- **Usage:** [Usage Guide](../usage.md)
- **Home:** [Documentation Home](../index.md)

## Related Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django ORM Reference](https://docs.djangoproject.com/en/stable/topics/db/)
- [Django Signals](https://docs.djangoproject.com/en/stable/topics/signals/)
- [PostgreSQL Schemas](https://www.postgresql.org/docs/current/ddl-schemas.html)

---

**Last Updated:** 2024
