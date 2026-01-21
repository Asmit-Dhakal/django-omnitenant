# django-omnitenant

![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Django](https://img.shields.io/badge/django-3.2%2B-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Stars](https://img.shields.io/github/stars/django-omnitenant/django-omnitenant.svg?style=flat)

**Multi-tenancy made simple for Django applications!**

---

## 🚀 Overview

**django-omnitenant** is a powerful, flexible multi-tenancy solution for Django that allows you to efficiently manage multiple isolated tenants within a single Django application. Whether you're building a SaaS platform, a shared hosting environment, or a complex multi-tenant application, django-omnitenant provides the tools you need to handle tenant isolation at the database, schema, or hybrid level.

### Key Features

- ✔ **Flexible Tenant Isolation** – Choose between database-per-tenant, schema-per-tenant, or hybrid isolation strategies(Coming soon...)
- ✔ **Automatic Tenant Context** – Seamlessly switch between tenants with context managers
- ✔ **Admin Restrictions** – Restrict admin access to tenant-specific models
- ✔ **Tenant-Aware Middleware** – Automatically resolve tenants from HTTP requests
- ✔ **Tenant-Aware Caching** – Cache keys prefixed with tenant IDs
- ✔ **Tenant-Aware Celery** – Run Celery tasks in the context of a specific tenant
- ✔ **Comprehensive CLI Tools** – Create, manage, and migrate tenants with ease
- ✔ **Signal System** – Hook into tenant lifecycle events (creation, deletion, migration)
- ✔ **Customizable Tenant Resolution** – Resolve tenants from subdomains, custom domains, or other sources

---

## ✨ Features

### **Multi-Tenancy Strategies**

- **Database-per-Tenant**: Each tenant has its own database
- **Schema-per-Tenant**: All tenants share a single database but have separate schemas
- **Hybrid(soon...)**: Combine database and schema isolation for complex scenarios

### **Tenant Management**

- Create, delete, and manage tenants with a simple CLI
- Run migrations for individual tenants or all tenants at once
- Create superusers within specific tenants

### **Tenant-Aware Components**

- **Middleware**: Automatically resolves tenants from HTTP requests
- **Database Router**: Routes queries to the correct database/schema
- **Cache Backend**: Prefixes cache keys with tenant IDs
- **Celery Integration**: Run tasks in the context of a specific tenant

### **Security & Permissions**

- Restrict admin access to tenant-specific models
- Ensure tenant isolation at the database and schema level
- Validate tenant IDs and domain names

### **Extensible Architecture**

- Custom tenant models and domain models
- Custom tenant resolvers for flexible tenant resolution logic
- Patch system for extending Django's core functionality

---

## 🛠️ Tech Stack

- **Language**: Python 3.8+
- **Framework**: Django 3.2+
- **Database**: PostgreSQL (recommended), MySQL(only for db type isolation)
- **Dependencies**: Django, psycopg2 (for PostgreSQL), Celery (optional)
- **License**: MIT

---

## 📦 Installation

### Prerequisites

Before installing django-omnitenant, ensure you have the following:

- Python 3.8 or higher
- Django 3.2 or higher
- PostgreSQL (recommended) or another supported database
- Basic familiarity with Django and Python

### Quick Start

1. **Install django-omnitenant**:

```bash
pip install django-omnitenant
```

2. **Add to your `INSTALLED_APPS`**:

```python
# settings.py
INSTALLED_APPS = [
    ...
    'django_omnitenant',
    ...
]
```

3. **Configure django-omnitenant**:

Add the following to your `settings.py`:

```python
# settings.py
OMNITENANT_CONFIG = {
    'TENANT_MODEL': 'myapp.Tenant',  # Your custom tenant model
    'DOMAIN_MODEL': 'myapp.Domain',  # Your custom domain model
    'PUBLIC_HOST': 'localhost',      # Default public host
    'PUBLIC_TENANT_NAME': 'public_omnitenant',  # Default public tenant
    'MASTER_TENANT_NAME': 'Master',  # Master tenant name
    'PATCHES': [
    "your custom patches's full path"
    ],
}
```

4. **Run migrations**:

```bash
python manage.py migrate
```

5. **Add middleware**:

```python
# settings.py
MIDDLEWARE = [
    ...
    'django_omnitenant.middleware.TenantMiddleware',
    ...
]
```

6. **Configure your database router**:

```python
# settings.py
DATABASE_ROUTERS = [
    'django_omnitenant.routers.TenantRouter',
]
```

7. **Create your first tenant**:

```bash
python manage.py createtenantsuperuser --tenant-id=mytenant
```

---

## 🎯 Usage

### Basic Usage

#### Creating a Tenant

```bash
python manage.py createtenant
```

#### Running Migrations for a Tenant

```bash
python manage.py migratetenant --tenant-id=mytenant
```

#### Running Migrations for All Tenants

```bash
python manage.py migratealltenants
```

#### Shell with Tenant Context

```bash
python manage.py shell --tenant-id=mytenant
```

#### Show All Tenants

```bash
python manage.py showtenants
```

### Advanced Usage: Custom Tenant Model

1. **Define your tenant model**:

```python
# models.py
from django.db import models
from django_omnitenant.models import BaseTenant

class Tenant(BaseTenant):
    description = models.TextField(blank=True, null=True)
```

2. **Configure django-omnitenant**:

```python
# settings.py
OMNITENANT_CONFIG = {
    'TENANT_MODEL': 'myapp.Tenant',
    ...
}
```

### Advanced Usage: Custom Tenant Resolver

1. **Create a custom resolver**:

```python
# resolvers/custom_resolver.py
from django_omnitenant.resolvers.base import BaseTenantResolver
from django_omnitenant.utils import get_tenant_model

class CustomTenantResolver(BaseTenantResolver):
    def resolve(self, request):
        # Implement your custom logic to resolve the tenant
        tenant_id = request.GET.get('tenant_id')
        Tenant = get_tenant_model()
        return Tenant.objects.get(tenant_id=tenant_id)
```

2. **Configure the resolver**:

```python
# settings.py
OMNITENANT_CONFIG = {
    'TENANT_RESOLVER': 'myapp.resolvers.CustomTenantResolver',
    ...
}
```

### Advanced Usage: Tenant-Aware Admin

```python
# admin.py
from django.contrib import admin
from django_omnitenant.admin import _TenantRestrictAdminMixin

class MyModelAdmin(_TenantRestrictAdminMixin, admin.ModelAdmin):
    pass

admin.site.register(MyModel, MyModelAdmin)
```

---

## 📁 Project Structure

```
django-omnitenant/
├── __init__.py
├── admin.py
├── apps.py
├── bootstrap.py
├── conf.py
├── constants.py
├── exceptions.py
├── middleware.py
├── models.py
├── routers.py
├── signals.py
├── tenant_context.py
├── utils.py
├── validators.py
├── views.py
├── backends/
│   ├── __init__.py
│   ├── base.py
│   ├── cache_backend.py
│   ├── database_backend.py
│   ├── postgresql/
│   │   ├── __init__.py
│   │   └── base.py
│   └── schema_backend.py
├── management/
│   └── commands/
│       ├── createtenant.py
│       ├── createsuperuser.py
│       ├── migratealltenants.py
│       ├── migratetenant.py
│       ├── shell.py
│       └── showtenants.py
├── patches/
│   ├── cache.py
│   └── celery.py
├── resolvers/
│   ├── __init__.py
│   ├── base.py
│   ├── customdomain_resolver.py
│   └── subdomain_resolver.py
├── tests/
│   └── testcases.py
└── migrations/
```

---

## 🔧 Configuration

### Environment Variables

No environment variables are required, but you can customize django-omnitenant by setting the following in your `settings.py`:

```python
# Database and Cache Configuration
MASTER_DB_ALIAS = 'default'
PUBLIC_DB_ALIAS = 'public'
MASTER_CACHE_ALIAS = 'default'

# Tenant Configuration
MASTER_TENANT_NAME = 'Master'
PUBLIC_TENANT_NAME = 'public_omnitenant'
DEFAULT_SCHEMA_NAME = 'public'

# Tenant Model Configuration
OMNITENANT_CONFIG = {
    'TENANT_MODEL': 'myapp.Tenant',
    'DOMAIN_MODEL': 'myapp.Domain',
    'PUBLIC_HOST': 'localhost',
    'PUBLIC_TENANT_NAME': 'public_omnitenant',
    'MASTER_TENANT_NAME': 'Master',
    'PATCHES': [
        'django_omnitenant.patches.cache',
        'django_omnitenant.patches.celery',
    ],
}
```

### Customizing Tenant Models

To customize your tenant model, create a model that inherits from `BaseTenant`:

```python
# models.py
from django.db import models
from django_omnitenant.models import BaseTenant

class Tenant(BaseTenant):
    description = models.TextField(blank=True, null=True)
```

### Customizing Domain Models

To customize your domain model, create a model that represents domains and link it to tenants:

```python
# models.py
from django.db import models
from django_omnitenant.models import BaseTenant

class Domain(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    def __str__(self):
        return self.domain
```

---

## 🤝 Contributing

We welcome contributions from the community! Here's how you can contribute to django-omnitenant:

### Development Setup

1. **Clone the repository**:

```bash
git clone https://github.com/yourusername/django-omnitenant.git
cd django-omnitenant
```

2. **Create a virtual environment**:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. **Install dependencies**:

```bash
pip install -e .
```

4. **Run tests**:

```bash
python -m pytest tests/
```

### Code Style Guidelines

- Follow PEP 8 style guidelines
- Use type hints where possible
- Write clear, concise, and well-documented code
- Ensure tests cover all functionality

### Pull Request Process

1. Fork the repository and create your branch from `master`.
2. Make your changes and ensure they pass all tests.
3. Submit a pull request with a clear description of your changes.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors & Contributors

**Maintainers**:

- [Krishna Rimal](https://github.com/RahulRimal) - Initial work and ongoing maintenance

**Contributors**:

- Contributors are welcomed

---

## 🐛 Issues & Support

### Reporting Issues

If you encounter any issues or have feature requests, please open an issue on the [GitHub Issues](https://github.com/RahulRimal/django-omnitenant/issues) page.

### Getting Help

- **Documentation**: Check out the [wiki](https://github.com/RahulRimal/django-omnitenant/wiki) for detailed guides.
- **FAQ**: Common questions and answers can be found in the [FAQ](https://github.com/RahulRimal/django-omnitenant/wiki/FAQ) section.

---

## 🗺️ Roadmap

### Planned Features

- **Hybrid Isolation**: Combine database and schema isolation for more complex scenarios
- **Tenant Analytics**: Built-in tools for monitoring and analyzing tenant usage
- **Tenant Provisioning API**: RESTful API for programmatically creating and managing tenants
- **Improved Documentation**: More detailed guides and tutorials

### Known Issues

- **PostgreSQL 16 Compatibility**: Testing and ensuring compatibility with PostgreSQL 15
- **Celery Task Persistence**: Improving task persistence across tenant switches

### Future Improvements

- **Better Performance**: Optimize database and cache operations for better performance
- **Enhanced Security**: Additional security features and validations
- **More Resolvers**: Additional tenant resolution strategies

---

## 🌟 Star and Share

If you find django-omnitenant useful, please consider giving it a star on GitHub! Sharing it with your network helps us reach more developers and continue improving the project.

Thank you for using django-omnitenant! 🚀
