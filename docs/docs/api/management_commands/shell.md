# Shell Command

`python manage.py shell [--tenant-id=<tenant_id>]`

## Overview

Extended Django shell with optional tenant context activation for interactive tenant-specific debugging and administration.

## Purpose

Enables interactive Python shell for debugging, testing, and administration with automatic tenant context:
- Execute Python code with tenant context
- Test tenant-specific functionality
- Debug multi-tenant issues
- Administer tenant data
- Run tenant-scoped queries

## Usage

### Without Tenant (Default Django Shell)

```bash
python manage.py shell
```

Standard Django shell without tenant context.

### With Tenant Context

```bash
python manage.py shell --tenant-id=acme
```

Opens shell with ACME tenant context automatically activated.

## Interactive Shell

### Without Tenant Context

```bash
$ python manage.py shell
Python 3.10.0 (default, Oct 6 2021, 00:00:00)
[GCC 10.3.0] :: Python 3.10.0+
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>>
```

### With Tenant Context

```bash
$ python manage.py shell --tenant-id=acme
Tenant 'acme' activated.
Python 3.10.0 (default, Oct 6 2021, 00:00:00)
[GCC 10.3.0] :: Python 3.10.0+
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>>
```

## Examples

### Query Tenant Data

With tenant context activated:

```python
>>> from myapp.models import User
>>> users = User.objects.all()
# Queries only users in 'acme' tenant
>>> print(users.count())
42

>>> user = users.first()
>>> print(user.email)
john@acme.com
```

### Test Tenant-Specific Logic

```python
>>> from django_omnitenant.tenant_context import TenantContext
>>> tenant = TenantContext.get_tenant()
>>> print(tenant.tenant_id)
acme

>>> from myapp.services import generate_report
>>> report = generate_report()
# Report generated using acme's data
```

### Modify Tenant Data

```python
>>> from myapp.models import Product
>>> p = Product.objects.create(
...     name="Acme Product",
...     price=99.99
... )
# Created in acme tenant only

>>> Product.objects.count()
1  # Acme's products only
```

### Compare Across Tenants

Without tenant context:

```python
>>> from django_omnitenant.models import Tenant
>>> from django_omnitenant.tenant_context import TenantContext
>>> from myapp.models import User

# Get acme users
>>> with TenantContext.use_tenant(Tenant.objects.get(tenant_id='acme')):
...     acme_users = User.objects.all()
...     print(f"Acme users: {acme_users.count()}")
Acme users: 42

# Get globex users
>>> with TenantContext.use_tenant(Tenant.objects.get(tenant_id='globex')):
...     globex_users = User.objects.all()
...     print(f"Globex users: {globex_users.count()}")
Globex users: 27
```

## Environment Setup

Django shell automatically imports:

```python
# Available in shell:
from django.db import models
from django.apps import apps
from django.conf import settings

# With tenant context:
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.models import Tenant

# Your models:
from myapp.models import *
```

## Debug Tenant Context

Check current tenant:

```python
>>> from django_omnitenant.tenant_context import TenantContext
>>> tenant = TenantContext.get_tenant()
>>> print(f"Tenant: {tenant.tenant_id}")
Tenant: acme

>>> print(f"Name: {tenant.name}")
Name: ACME Corporation

>>> print(f"Isolation: {tenant.isolation_type}")
Isolation: DATABASE
```

## Scripting

### Create Script File

```python
# script.py
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.models import Tenant
from myapp.models import User

# Get acme tenant
acme = Tenant.objects.get(tenant_id='acme')

# Enter tenant context
with TenantContext.use_tenant(acme):
    users = User.objects.all()
    print(f"Total users: {users.count()}")
    
    for user in users:
        print(f"  - {user.email}")
```

### Run Script in Shell

```bash
python manage.py shell < script.py
```

Or use shell_plus (IPython) if available:

```bash
python manage.py shell_plus --tenant-id=acme < script.py
```

## Advanced Features

### IPython Shell

If IPython installed, use enhanced shell:

```bash
python manage.py shell_plus --tenant-id=acme
# Opens IPython with all models auto-imported
```

Features:
- Syntax highlighting
- Tab completion
- History
- Better error messages

### Django Extensions

With django-extensions installed:

```bash
python manage.py shell_plus
# Auto-imports all models

# Then use tenant context manually:
>>> from django_omnitenant.tenant_context import TenantContext
>>> with TenantContext.use_tenant(acme_tenant):
...     user = User.objects.first()
```

## Troubleshooting

### Tenant Not Found

```python
>>> python manage.py shell --tenant-id=unknown
Tenant with ID 'unknown' does not exist.
```

Verify tenant_id is correct.

### Empty Query Results

```python
>>> User.objects.all()
# Returns 0 results
```

Verify:
- Correct tenant activated
- Data exists in tenant database
- Queries scoped to tenant

## Performance Tips

- Use `select_related()` and `prefetch_related()` for efficient queries
- Filter data early to reduce memory usage
- Use `.count()` instead of `len()` for large querysets
- Exit shell to free database connections

## Related Commands

- `createtenant` - Create new tenant
- `createtenantsuperuser` - Create admin user
- `migratetenant` - Run migrations
- `showtenants` - List all tenants
