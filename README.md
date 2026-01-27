# django-omnitenant

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-3.2%2B-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/django-omnitenant.svg)](https://pypi.org/project/django-omnitenant/)

A comprehensive multi-tenancy solution for Django that simplifies building scalable SaaS applications with flexible tenant isolation strategies.

## Overview

**django-omnitenant** is a production-ready Django application for implementing multi-tenancy in your Django projects. It provides out-of-the-box support for multiple tenant isolation strategies, automatic tenant context management, and comprehensive management commands for tenant lifecycle operations.

### Why django-omnitenant?

- **Multiple Isolation Strategies**: Support for database-per-tenant and schema-per-tenant isolation
- **Transparent Tenant Context**: Thread-safe tenant context management using Python's `contextvars`
- **Production-Ready**: Battle-tested patterns for multi-tenant Django applications
- **Extensible Design**: Pluggable resolvers, backends, and patch system
- **Developer Friendly**: Comprehensive CLI tools and intuitive API
- **Signal Integration**: Django signals at key tenant lifecycle events

## Features

### Core Functionality

- **Multi-Tenant Isolation**: Choose between:
  - **Database-per-Tenant**: Each tenant isolated in a separate database
  - **Schema-per-Tenant**: All tenants share a database but use separate PostgreSQL schemas
  
- **Tenant Resolution**: Multiple strategies for identifying the current tenant:
  - Custom domain resolver
  - Subdomain resolver
  - Extensible resolver interface for custom implementations

- **Automatic Context Management**: Thread-safe tenant context with context managers for seamless tenant switching

- **Tenant-Aware Components**:
  - Database routing with automatic query isolation
  - Cache backend with tenant-scoped keys
  - Celery task integration for tenant-aware background jobs
  - Admin interface restrictions for tenant data isolation

### Management Commands

Comprehensive CLI for tenant operations:

- `createtenant` - Create new tenants interactively
- `createtenantsuperuser` - Create admin users per tenant
- `migratetenant` - Run migrations for specific tenants
- `migratealltenants` - Batch migrate all tenants
- `shell` - Django shell with tenant context
- `showtenants` - List and export tenant information

### Security & Validation

- DNS label validation for tenant identifiers
- Domain name validation for custom domains
- Admin access restrictions to tenant-specific models
- Tenant data isolation at the database/schema level

## Requirements

- Python 3.8+
- Django 3.2+
- PostgreSQL 10+ (recommended for schema isolation)
- psycopg2-binary (for PostgreSQL support)

Optional dependencies:

- Celery (for async task support)
- Redis (for distributed caching)

## Installation

### Via pip

```bash
pip install django-omnitenant
```

### From source

```bash
git clone https://github.com/RahulRimal/django-omnitenant.git
cd django-omnitenant
pip install -e .
```

## Quick Start

### 1. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    # ...
    'myapp',  # Your application
    'django_omnitenant',
]
```

### 2. Configure django-omnitenant

```python
# settings.py
OMNITENANT_CONFIG = {
    'TENANT_MODEL': 'myapp.Tenant',
    'DOMAIN_MODEL': 'myapp.Domain',
    'PUBLIC_HOST': 'example.com',
    'PUBLIC_TENANT_NAME': 'public',
    'MASTER_TENANT_NAME': 'master',
    'TENANT_RESOLVER': 'django_omnitenant.resolvers.CustomDomainTenantResolver',
}
```

### 3. Create Tenant Models

```python
# myapp/models.py
from django.db import models
from django_omnitenant.models import BaseTenant, BaseDomain

class Tenant(BaseTenant):
    """Custom tenant model extending BaseTenant."""
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Domain(BaseDomain):
    """Custom domain model linking domains to tenants."""
    pass
```

### 4. Add Middleware

```python
# settings.py
MIDDLEWARE = [
    # ... other middleware
    'django_omnitenant.middleware.TenantMiddleware',
    # ... other middleware
]
```

### 5. Configure Database Router

```python
# settings.py
DATABASE_ROUTERS = [
    'django_omnitenant.routers.TenantRouter',
]
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create Your First Tenant

```bash
python manage.py createtenant
# Follow the interactive prompts to create a tenant
```

## Usage Guide

### Creating Tenants

#### Interactive Mode

```bash
python manage.py createtenant
```

The command will prompt for:

- Tenant ID (unique identifier)
- Tenant Name (display name)
- Isolation Type (database or schema)
- Database credentials (for database isolation)

#### Programmatic Creation

```python
from django_omnitenant.utils import get_tenant_model, get_tenant_backend

Tenant = get_tenant_model()

# Create tenant
tenant = Tenant.objects.create(
    tenant_id='acme',
    name='ACME Corporation',
    isolation_type=Tenant.IsolationType.DATABASE,  # or SCHEMA
    config={
        'db_config': {
            'NAME': 'acme_db',
            'USER': 'acme_user',
            'PASSWORD': 'secure_password',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }
)

# Provision resources and run migrations
backend = get_tenant_backend(tenant)
backend.create(run_migrations=True)
```

### Accessing Tenant Data

#### In Views

```python
from django.http import JsonResponse

def my_view(request):
    # Tenant is automatically resolved and set by middleware
    tenant = request.tenant
    return JsonResponse({'tenant': tenant.tenant_id})
```

#### In Models

Use the tenant-aware manager:

```python
from django_omnitenant.models import TenantQuerySetManager

class MyModel(models.Model):
    name = models.CharField(max_length=255)
    objects = TenantQuerySetManager()
    
    class Meta:
        # Queries are automatically scoped to current tenant
        pass
```

Query within tenant context:

```python
from django_omnitenant.tenant_context import TenantContext

with TenantContext.use_tenant(tenant):
    items = MyModel.objects.all()  # Queries tenant's database/schema
```

### Managing Tenant Lifecycle

#### Running Migrations

```bash
# Migrate specific tenant
python manage.py migratetenant --tenant-id=acme

# Migrate all tenants
python manage.py migratealltenants

# Show migration plan
python manage.py migratetenant --tenant-id=acme --plan
```

#### Creating Superusers

```bash
python manage.py createtenantsuperuser --tenant-id=acme
```

#### Viewing Tenants

```bash
# List all tenants
python manage.py showtenants

# Export as JSON
python manage.py showtenants --format=json

# Export as CSV
python manage.py showtenants --format=csv

# Filter by isolation type
python manage.py showtenants --isolation-type=database
```

#### Interactive Shell

```bash
# Shell with tenant context
python manage.py shell --tenant-id=acme

# Inside the shell
>>> from myapp.models import MyModel
>>> MyModel.objects.all()  # Queries only acme's data
```

### Advanced: Custom Tenant Resolver

Create a custom resolver for specialized tenant resolution logic:

```python
# myapp/resolvers.py
from django_omnitenant.resolvers.base import BaseTenantResolver
from django_omnitenant.exceptions import TenantNotFound

class HeaderTenantResolver(BaseTenantResolver):
    """Resolve tenant from HTTP header."""
    
    def resolve(self, request):
        """Extract tenant from X-Tenant-ID header."""
        from django_omnitenant.utils import get_tenant_model
        
        tenant_id = request.headers.get('X-Tenant-ID')
        if not tenant_id:
            raise TenantNotFound("No X-Tenant-ID header provided")
        
        Tenant = get_tenant_model()
        try:
            return Tenant.objects.get(tenant_id=tenant_id)
        except Tenant.DoesNotExist:
            raise TenantNotFound(f"Tenant '{tenant_id}' not found")
```

Configure in settings:

```python
# settings.py
OMNITENANT_CONFIG = {
    'TENANT_RESOLVER': 'myapp.resolvers.HeaderTenantResolver',
}
```

### Advanced: Tenant-Aware Admin

Restrict admin access to tenant-specific data:

```python
# myapp/admin.py
from django.contrib import admin
from django_omnitenant.admin import TenantRestrictAdminMixin
from .models import MyModel

@admin.register(MyModel)
class MyModelAdmin(TenantRestrictAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'created_at']
    # Admin access restricted to master tenant only
```

### Background Tasks with Celery

```python
# myapp/tasks.py
from celery import shared_task
from django_omnitenant.tenant_context import TenantContext

@shared_task
def process_tenant_data(tenant_id):
    """Process data for specific tenant."""
    from django_omnitenant.utils import get_tenant_model
    
    Tenant = get_tenant_model()
    tenant = Tenant.objects.get(tenant_id=tenant_id)
    
    with TenantContext.use_tenant(tenant):
        # Task runs in tenant context
        pass
```

Call from your code:

```python
process_tenant_data.delay(tenant_id='acme')
```

### Context Managers

Switch tenant context for specific operations:

```python
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_tenant_model

Tenant = get_tenant_model()
acme_tenant = Tenant.objects.get(tenant_id='acme')

# Temporarily switch to tenant
with TenantContext.use_tenant(acme_tenant):
    # All queries here use acme's database/schema
    items = MyModel.objects.all()

# Back to original context

# Switch to master database
with TenantContext.use_master_db():
    # Access master database
    pass

# Switch to specific schema
with TenantContext.use_schema('tenant_acme'):
    # Access specific schema
    pass
```

## Configuration Reference

### Required Settings

```python
OMNITENANT_CONFIG = {
    # Database and schema settings
    'TENANT_MODEL': 'myapp.Tenant',        # Path to tenant model
    'DOMAIN_MODEL': 'myapp.Domain',        # Path to domain model
    
    # Request resolution
    'PUBLIC_HOST': 'example.com',          # Default public host
    'TENANT_RESOLVER': 'django_omnitenant.resolvers.CustomDomainTenantResolver',
    
    # Tenant identification
    'PUBLIC_TENANT_NAME': 'public',        # Public/shared tenant
    'MASTER_TENANT_NAME': 'master',        # Master tenant (shared data)
    
    # Optional patches
    'PATCHES': [
        'django_omnitenant.patches.cache',
        'django_omnitenant.patches.celery',
    ],
}
```

### Optional Settings

```python
# Database aliases
MASTER_DB_ALIAS = 'default'                # Master database alias
PUBLIC_DB_ALIAS = 'default'                # Public database alias
MASTER_CACHE_ALIAS = 'default'             # Master cache alias

# Schema settings
DEFAULT_SCHEMA_NAME = 'public'              # Default PostgreSQL schema
```

### Built-in Resolvers

- `django_omnitenant.resolvers.CustomDomainTenantResolver` - Resolve from custom domain
- `django_omnitenant.resolvers.SubdomainTenantResolver` - Resolve from subdomain

## Architecture

### Isolation Strategies

#### Database-per-Tenant

Each tenant has a dedicated database:

```
Master Database          Tenant Databases
┌─────────────────┐      ┌──────────────┐
│ Tenants         │      │ tenant_acme  │
│ Domains         │      └──────────────┘
│ Shared Config   │      ┌──────────────┐
└─────────────────┘      │ tenant_globex│
                         └──────────────┘
```

**Pros**: Complete isolation, independent scaling
**Cons**: More infrastructure, connection overhead

#### Schema-per-Tenant

All tenants share a database with separate schemas:

```
Single Database
┌──────────────────────────────┐
│ public schema                │
│ ├─ tenants                   │
│ ├─ domains                   │
│ └─ shared tables             │
│                              │
│ tenant_acme schema           │
│ ├─ users                     │
│ ├─ products                  │
│ └─ orders                    │
│                              │
│ tenant_globex schema         │
│ ├─ users                     │
│ ├─ products                  │
│ └─ orders                    │
└──────────────────────────────┘
```

**Pros**: Shared infrastructure, simpler management, faster schema creation
**Cons**: Less isolation, shared connection pool

### Component Overview

- **Middleware**: Resolves tenant from HTTP request
- **Router**: Routes queries to correct database/schema
- **Context**: Thread-safe tenant context using `contextvars`
- **Backends**: Handle provisioning (database/schema creation)
- **Resolvers**: Extract tenant from request using various strategies
- **Signals**: Emit events at tenant lifecycle stages
- **Management Commands**: CLI tools for tenant operations

## Testing

Use provided test case mixins:

```python
from django_omnitenant.tests.testcases import (
    BaseTenantTestCase,
    DBTenantTestCase,
    SchemaTenantTestCase,
)

class MyTestCase(DBTenantTestCase):
    """Tests for database-per-tenant isolation."""
    
    def test_tenant_isolation(self):
        # Test case automatically sets up tenant context
        from myapp.models import MyModel
        
        # Create data in tenant
        MyModel.objects.create(name='Test')
        
        # Verify isolation
        assert MyModel.objects.count() == 1
```

## API Reference

### Key Classes and Functions

#### Tenant Context

- [`TenantContext`](docs/docs/api/core/tenant_context.md) - Manage tenant context
- Methods: `get_tenant()`, `use_tenant()`, `use_master_db()`, `use_schema()`

#### Models

- [`BaseTenant`](docs/docs/api/models.md) - Abstract tenant model
- [`BaseDomain`](docs/docs/api/models.md) - Abstract domain model
- [`TenantQuerySetManager`](docs/docs/api/models.md) - Tenant-aware query manager

#### Backends

- [`BaseTenantBackend`](docs/docs/api/backends/base.md) - Abstract backend
- [`DatabaseTenantBackend`](docs/docs/api/backends/database_backend.md) - Database isolation
- [`SchemaTenantBackend`](docs/docs/api/backends/schema_backend.md) - Schema isolation
- [`CacheTenantBackend`](docs/docs/api/backends/cache_backend.md) - Cache management

#### Utilities

- [`get_tenant_model()`](docs/docs/api/core/utils.md) - Get configured tenant model
- [`get_domain_model()`](docs/docs/api/core/utils.md) - Get configured domain model
- [`get_tenant_backend()`](docs/docs/api/core/utils.md) - Get backend for tenant
- [`get_current_tenant()`](docs/docs/api/core/utils.md) - Get current tenant

#### Exceptions

- [`TenantNotFound`](docs/docs/api/core/exceptions.md) - Tenant resolution failed
- [`DomainNotFound`](docs/docs/api/core/exceptions.md) - Domain resolution failed

See [full API documentation](docs/docs/api/) for complete reference.

## Common Patterns

### Multi-Tenant Serializers (DRF)

```python
from rest_framework import serializers
from django_omnitenant.tenant_context import TenantContext

class TenantAwareSerializer(serializers.ModelSerializer):
    def validate(self, data):
        # Validations run in current tenant context
        return data
```

### Cross-Tenant Queries

```python
from django_omnitenant.tenant_context import TenantContext

for tenant in Tenant.objects.using('default').all():
    with TenantContext.use_tenant(tenant):
        # Query in each tenant's context
        count = MyModel.objects.count()
        print(f"{tenant.name}: {count} items")
```

### Tenant Migration Hooks

```python
from django_omnitenant.signals import tenant_created, tenant_migrated

@receiver(tenant_created)
def setup_tenant(sender, tenant, **kwargs):
    """Run custom setup after tenant creation."""
    pass

@receiver(tenant_migrated)
def post_migration_setup(sender, tenant, **kwargs):
    """Run custom setup after migrations."""
    pass
```

## Performance Considerations

- **Connection Pooling**: Use `CONN_MAX_AGE` in DATABASES settings
- **Query Optimization**: Add indexes per tenant database/schema
- **Caching Strategy**: Use tenant-scoped cache keys (automatic)
- **Signal Handlers**: Keep signal handlers lightweight
- **Bulk Operations**: Use `bulk_create()` and `bulk_update()` in tenant context

## Security Best Practices

1. **Validate Tenant Access**: Always verify tenant context in views
2. **Secure Credentials**: Store DB credentials securely (env variables, vaults)
3. **Audit Logging**: Log cross-tenant operations
4. **Rate Limiting**: Implement per-tenant rate limiting
5. **Data Isolation**: Verify isolation with security tests
6. **Admin Access**: Restrict admin to master tenant
7. **Signal Security**: Validate tenant context in signal handlers

## Troubleshooting

### Tenant Not Found

```python
# Error: TenantNotFound
# Solution: Verify TENANT_RESOLVER configuration and domain mapping
```

### Query Runs on Wrong Database

```python
# Error: Data queried from wrong tenant
# Solution: Ensure TenantMiddleware is in MIDDLEWARE
# or explicitly use TenantContext.use_tenant()
```

### Migrations Fail

```bash
# Error: Migration fails for specific tenant
# Solution: Run with --no-input flag
python manage.py migratetenant --tenant-id=acme --no-input
```

See [Troubleshooting Guide](docs/docs/api/management_commands/) for more.

## Development

### Running Tests

```bash
# Clone repository
git clone https://github.com/RahulRimal/django-omnitenant.git
cd django-omnitenant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=django_omnitenant
```

### Code Style

- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://github.com/psf/black) for formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Type hints required for public APIs

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes and breaking changes.

## Roadmap

- [ ] Hybrid isolation strategy (database + schema)
- [ ] REST API for tenant management
- [ ] Tenant analytics dashboard
- [ ] Performance monitoring tools
- [ ] Multi-database support (MySQL, Oracle)

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Support

### Getting Help

- **Documentation**: [Read the Docs](https://django-omnitenant.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/RahulRimal/django-omnitenant/issues)
- **Discussions**: [GitHub Discussions](https://github.com/RahulRimal/django-omnitenant/discussions)

### Reporting Issues

Please include:

- Django version
- Python version
- Isolation strategy used
- Minimal reproducible example
- Error traceback

## Citation

If you use django-omnitenant in your research, please cite:

```bibtex
@software{rimal2024django-omnitenant,
  author = {Krishna Rimal},
  title = {django-omnitenant: Multi-tenancy for Django},
  url = {https://github.com/RahulRimal/django-omnitenant},
  year = {2024},
}
```

## Acknowledgments

- Inspired by [django-tenant-schemas](https://github.com/tomturner/django-tenant-schemas)
- Built for modern Django applications
- Special thanks to the Django community

---

**Made with ❤️ by [Ajna Lab](https://ajnalab.com/) for the Django community**
