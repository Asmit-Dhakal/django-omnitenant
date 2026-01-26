---
hide:
  - navigation
---




# Usage Guide

## Overview

This guide covers common usage patterns for django-omnitenant. Learn how to create tenants, access tenant data, manage migrations, and handle advanced scenarios.

## Table of Contents

- [Creating Tenants](#creating-tenants)
- [Tenant Models](#tenant-models)
- [Accessing Tenant Data](#accessing-tenant-data)
- [Tenant Context](#tenant-context)
- [Database Queries](#database-queries)
- [Managing Migrations](#managing-migrations)
- [Admin Interface](#admin-interface)
- [Celery Integration](#celery-integration)
- [Testing](#testing)
- [Common Patterns](#common-patterns)

## Creating Tenants

### Interactive Creation

The easiest way to create tenants is using the management command:

```bash
python manage.py createtenant
```

This launches an interactive prompt:

```
Starting tenant creation...
Enter tenant ID (unique): acme
Enter tenant name: ACME Corporation
Select isolation type (database/schema/table/cache): database
Do you want to create the database now? (y/n): y
Enter database name for tenant: acme_db
Enter database user: acme_user
Enter database password: ****
Enter database host: localhost
Enter database port (default: 5432): 5432
Do you want to run migrations for this tenant now? (y/n): y
```

### Programmatic Creation

Create tenants in Python code:

```python
from django_omnitenant.utils import get_tenant_model, get_tenant_backend

Tenant = get_tenant_model()

# Create tenant record
tenant = Tenant.objects.create(
    tenant_id='acme',
    name='ACME Corporation',
    isolation_type=Tenant.IsolationType.DATABASE,
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

# Provision resources (create database/schema)
backend = get_tenant_backend(tenant)
backend.create(run_migrations=True)
```

### Bulk Creation

Create multiple tenants:

```python
from django_omnitenant.utils import get_tenant_model, get_tenant_backend

Tenant = get_tenant_model()

tenants_data = [
    {
        'tenant_id': 'acme',
        'name': 'ACME Corporation',
        'isolation_type': Tenant.IsolationType.DATABASE,
    },
    {
        'tenant_id': 'globex',
        'name': 'Globex Inc',
        'isolation_type': Tenant.IsolationType.SCHEMA,
    },
]

for data in tenants_data:
    tenant = Tenant.objects.create(**data)
    backend = get_tenant_backend(tenant)
    backend.create(run_migrations=True)
    print(f"Created tenant: {tenant.name}")
```

## Tenant Models

### BaseTenant Model

Define your tenant model by extending `BaseTenant`:

```python
from django.db import models
from django_omnitenant.models import BaseTenant, BaseDomain

class Tenant(BaseTenant):
    """Organization/Customer tenant model."""
    
    description = models.TextField(blank=True)
    max_users = models.IntegerField(default=10)
    subscription_tier = models.CharField(
        max_length=20,
        choices=[('free', 'Free'), ('pro', 'Pro'), ('enterprise', 'Enterprise')],
        default='free'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_user_count(self):
        """Get number of users in this tenant."""
        from django.contrib.auth.models import User
        return User.objects.filter(profile__tenant=self).count()
```

### BaseDomain Model

Map domains to tenants:

```python
from django_omnitenant.models import BaseDomain

class Domain(BaseDomain):
    """Custom domain for tenant."""
    
    is_primary = models.BooleanField(default=False)
    ssl_certificate = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('domain', 'tenant')
    
    def __str__(self):
        return f"{self.domain} -> {self.tenant.name}"
```

### Register Models

Configure in `settings.py`:

```python
OMNITENANT_CONFIG = {
    'TENANT_MODEL': 'myapp.Tenant',
    'DOMAIN_MODEL': 'myapp.Domain',
}
```

## Accessing Tenant Data

### In Views

Tenant is automatically available in request:

```python
from django.shortcuts import render
from django.http import JsonResponse

def dashboard(request):
    # Tenant automatically resolved by middleware
    tenant = request.tenant
    
    return JsonResponse({
        'tenant_id': tenant.tenant_id,
        'tenant_name': tenant.name,
        'subscription': tenant.subscription_tier,
    })
```

### In Models

Use `TenantQuerySetManager` for automatic scoping:

```python
from django.db import models
from django_omnitenant.models import TenantQuerySetManager

class Project(models.Model):
    """Project belonging to a tenant."""
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    objects = TenantQuerySetManager()
    
    def __str__(self):
        return self.name
```

Query in tenant context:

```python
from django_omnitenant.tenant_context import TenantContext

# All queries automatically filtered to current tenant
projects = Project.objects.all()
project = Project.objects.get(id=1)
```

### Across Models

Query related data:

```python
from django_omnitenant.tenant_context import TenantContext

# Using select_related for efficiency
projects = Project.objects.select_related('tenant').all()

# Using prefetch_related
projects = Project.objects.prefetch_related('tasks').all()

# Filtering
active_projects = Project.objects.filter(
    status='active'
).order_by('-created_at')
```

## Tenant Context

### Switching Tenants

Use context managers to switch tenant context:

```python
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_tenant_model

Tenant = get_tenant_model()
acme_tenant = Tenant.objects.get(tenant_id='acme')

# Temporarily switch to tenant context
with TenantContext.use_tenant(acme_tenant):
    # All queries use acme's database/schema
    projects = Project.objects.all()
    print(f"ACME has {projects.count()} projects")

# Context automatically restored
print("Back to original context")
```

### Getting Current Tenant

```python
from django_omnitenant.tenant_context import TenantContext

# In view
def my_view(request):
    current_tenant = request.tenant
    # or
    current_tenant = TenantContext.get_tenant()
    return JsonResponse({'tenant': current_tenant.tenant_id})
```

### Master Database Access

Access shared/master database:

```python
from django_omnitenant.tenant_context import TenantContext

# Access master database (shared between tenants)
with TenantContext.use_master_db():
    # Query master database
    all_tenants = Tenant.objects.all()
    for tenant in all_tenants:
        print(f"Tenant: {tenant.name}")
```

### Schema Access

For schema-per-tenant isolation:

```python
from django_omnitenant.tenant_context import TenantContext

# Access specific schema
with TenantContext.use_schema('tenant_acme'):
    # Queries run on tenant_acme schema
    projects = Project.objects.all()
```

## Database Queries

### Basic Queries

All queries automatically scoped to current tenant:

```python
from myapp.models import Project, Task

# These automatically filter to current tenant
all_projects = Project.objects.all()
active_projects = Project.objects.filter(status='active')
project = Project.objects.get(id=1)
project_count = Project.objects.count()
```

### Filtering

```python
from datetime import timedelta
from django.utils import timezone

# Complex filtering
recent_projects = Project.objects.filter(
    created_at__gte=timezone.now() - timedelta(days=30),
    status='active'
).exclude(
    name__icontains='test'
)

# Q objects for complex conditions
from django.db.models import Q

projects = Project.objects.filter(
    Q(status='active') | Q(status='in_progress')
).order_by('-priority')
```

### Aggregations

```python
from django.db.models import Count, Sum, Avg

# Count projects
project_count = Project.objects.count()

# Sum values
total_hours = Task.objects.aggregate(
    total=Sum('hours_spent')
)['total'] or 0

# Average
avg_priority = Project.objects.aggregate(
    avg=Avg('priority')
)['avg']

# Group by
from django.db.models import Count
by_status = Project.objects.values('status').annotate(
    count=Count('id')
)
# Result: [{'status': 'active', 'count': 5}, ...]
```

### Bulk Operations

```python
from myapp.models import Project, Task

# Bulk create
projects_data = [
    Project(name='Project 1'),
    Project(name='Project 2'),
    Project(name='Project 3'),
]
Project.objects.bulk_create(projects_data)

# Bulk update
Project.objects.filter(
    status='inactive'
).update(status='archived')

# Delete
Project.objects.filter(
    created_at__lt=timezone.now() - timedelta(days=365)
).delete()
```

## Managing Migrations

### Create Migrations

```bash
# Create migrations for your app
python manage.py makemigrations myapp

# Show migration plan
python manage.py showmigrations myapp
```

### Migrate Master Database

```bash
# Migrate shared/master database
python manage.py migrate
```

### Migrate Single Tenant

```bash
# Migrate specific tenant
python manage.py migratetenant --tenant-id=acme

# Show migration plan
python manage.py migratetenant --tenant-id=acme --plan

# Migrate specific app only
python manage.py migratetenant --tenant-id=acme myapp

# Migrate to specific migration
python manage.py migratetenant --tenant-id=acme myapp 0002_auto
```

### Migrate All Tenants

```bash
# Run migrations for all tenants
python manage.py migratealltenants

# Show progress
python manage.py migratealltenants --verbosity=2

# Skip confirmation
python manage.py migratealltenants --no-input
```

### Migration Signals

Hook into migration process:

```python
from django.dispatch import receiver
from django_omnitenant.signals import tenant_migrated

@receiver(tenant_migrated)
def post_migration_setup(sender, tenant, **kwargs):
    """Run after migrations complete."""
    # Create default data for tenant
    from myapp.models import Config
    
    Config.objects.get_or_create(
        tenant=tenant,
        defaults={'theme': 'default'}
    )
```

## Admin Interface

### Tenant-Aware Admin

Restrict admin access to tenant-specific data:

```python
from django.contrib import admin
from django_omnitenant.admin import TenantRestrictAdminMixin
from myapp.models import Project

@admin.register(Project)
class ProjectAdmin(TenantRestrictAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description']
    
    # Admin access restricted to master tenant only
    # Tenant data filtered automatically in list view
```

### Create Tenant Superuser

```bash
# Interactive
python manage.py createtenantsuperuser --tenant-id=acme

# Automated
python manage.py createtenantsuperuser \
  --tenant-id=acme \
  --username=admin \
  --email=admin@acme.com \
  --noinput
```

### Custom Admin Mixin

```python
from django.contrib import admin
from django_omnitenant.tenant_context import TenantContext

class TenantFilterMixin(admin.ModelAdmin):
    """Automatically filter admin queryset to current tenant."""
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # If not superuser, filter to current tenant
        if not request.user.is_superuser:
            tenant = TenantContext.get_tenant()
            if tenant:
                qs = qs.filter(tenant=tenant)
        
        return qs
```

## Celery Integration

### Basic Task

```python
from celery import shared_task
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_tenant_model

@shared_task
def send_notification(user_id, message):
    """Send notification to user."""
    from django.contrib.auth.models import User
    
    user = User.objects.get(id=user_id)
    # Task executes in tenant context (automatic)
    print(f"Sending to {user.email}: {message}")
```

### Task with Tenant

```python
from django_omnitenant.patches.celery import TenantAwareTask

@shared_task(base=TenantAwareTask)
def process_tenant_data(tenant_id):
    """Process data for specific tenant."""
    from django_omnitenant.utils import get_tenant_model
    
    Tenant = get_tenant_model()
    tenant = Tenant.objects.get(tenant_id=tenant_id)
    
    # Task automatically runs in tenant context
    with TenantContext.use_tenant(tenant):
        from myapp.models import Project
        
        projects = Project.objects.all()
        for project in projects:
            # Process project
            pass
```

### Queue Task

```python
from myapp.tasks import send_notification, process_tenant_data

# Send task to queue
send_notification.delay(user_id=1, message='Hello!')

# Queue with tenant context
process_tenant_data.delay(tenant_id='acme')
```

### Celery Beat (Scheduled Tasks)

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'process-all-tenants': {
        'task': 'myapp.tasks.process_all_tenants',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
}
```

Task implementation:

```python
@shared_task
def process_all_tenants():
    """Process data for all tenants."""
    from django_omnitenant.utils import get_tenant_model
    
    Tenant = get_tenant_model()
    
    for tenant in Tenant.objects.all():
        process_tenant_data.delay(tenant_id=tenant.tenant_id)
```

## Testing

### Basic Test Case

```python
from django.test import TestCase
from django_omnitenant.utils import get_tenant_model

class ProjectTestCase(TestCase):
    def setUp(self):
        """Set up test tenant."""
        Tenant = get_tenant_model()
        self.tenant = Tenant.objects.create(
            tenant_id='test',
            name='Test Tenant'
        )
    
    def test_project_creation(self):
        """Test creating project in tenant."""
        from myapp.models import Project
        from django_omnitenant.tenant_context import TenantContext
        
        with TenantContext.use_tenant(self.tenant):
            project = Project.objects.create(
                name='Test Project',
                status='active'
            )
            
            self.assertEqual(project.name, 'Test Project')
            self.assertTrue(Project.objects.filter(id=project.id).exists())
```

### Multi-Tenant Tests

```python
from django.test import TestCase
from django_omnitenant.utils import get_tenant_model
from django_omnitenant.tenant_context import TenantContext

class MultiTenantTestCase(TestCase):
    def setUp(self):
        """Create multiple tenants."""
        Tenant = get_tenant_model()
        
        self.acme = Tenant.objects.create(
            tenant_id='acme',
            name='ACME'
        )
        
        self.globex = Tenant.objects.create(
            tenant_id='globex',
            name='Globex'
        )
    
    def test_isolation(self):
        """Test data isolation between tenants."""
        from myapp.models import Project
        
        # Create project in ACME
        with TenantContext.use_tenant(self.acme):
            Project.objects.create(name='ACME Project')
        
        # Create project in Globex
        with TenantContext.use_tenant(self.globex):
            Project.objects.create(name='Globex Project')
        
        # Verify isolation
        with TenantContext.use_tenant(self.acme):
            self.assertEqual(Project.objects.count(), 1)
            self.assertEqual(Project.objects.first().name, 'ACME Project')
        
        with TenantContext.use_tenant(self.globex):
            self.assertEqual(Project.objects.count(), 1)
            self.assertEqual(Project.objects.first().name, 'Globex Project')
```

### Test with Request

```python
from django.test import Client, TestCase
from django_omnitenant.utils import get_tenant_model

class ViewTestCase(TestCase):
    def setUp(self):
        """Set up test tenant and client."""
        Tenant = get_tenant_model()
        Domain = get_domain_model()
        
        self.tenant = Tenant.objects.create(
            tenant_id='test',
            name='Test'
        )
        
        Domain.objects.create(
            domain='test.localhost',
            tenant=self.tenant
        )
        
        self.client = Client()
    
    def test_dashboard_view(self):
        """Test dashboard view with tenant context."""
        response = self.client.get(
            '/dashboard/',
            HTTP_HOST='test.localhost'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('Test', response.content.decode())
```

## Common Patterns

### Create Tenant Signal

```python
from django.dispatch import receiver
from django_omnitenant.signals import tenant_created
from myapp.models import TenantConfig

@receiver(tenant_created)
def setup_new_tenant(sender, tenant, **kwargs):
    """Initialize tenant configuration."""
    TenantConfig.objects.create(
        tenant=tenant,
        theme='default',
        language='en'
    )
    
    print(f"Tenant {tenant.name} initialized")
```

### Custom Resolver

```python
from django_omnitenant.resolvers.base import BaseTenantResolver
from django_omnitenant.exceptions import TenantNotFound
from django_omnitenant.utils import get_tenant_model

class HeaderTenantResolver(BaseTenantResolver):
    """Resolve tenant from HTTP header."""
    
    def resolve(self, request):
        tenant_id = request.headers.get('X-Tenant-ID')
        
        if not tenant_id:
            raise TenantNotFound("X-Tenant-ID header required")
        
        Tenant = get_tenant_model()
        try:
            return Tenant.objects.get(tenant_id=tenant_id)
        except Tenant.DoesNotExist:
            raise TenantNotFound(f"Tenant '{tenant_id}' not found")
```

Configure in `settings.py`:

```python
OMNITENANT_CONFIG = {
    'TENANT_RESOLVER': 'myapp.resolvers.HeaderTenantResolver',
}
```

### DRF Serializer

```python
from rest_framework import serializers
from myapp.models import Project

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'status', 'created_at']
    
    def validate_name(self, value):
        """Validate project name is unique in tenant."""
        if Project.objects.filter(name=value).exists():
            raise serializers.ValidationError("Name already exists in this tenant")
        return value
```

### Cross-Tenant Reporting

```python
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_tenant_model
from myapp.models import Project

def get_all_tenant_stats():
    """Generate report across all tenants."""
    Tenant = get_tenant_model()
    stats = {}
    
    for tenant in Tenant.objects.all():
        with TenantContext.use_tenant(tenant):
            stats[tenant.tenant_id] = {
                'name': tenant.name,
                'projects': Project.objects.count(),
                'users': User.objects.count(),
            }
    
    return stats
```

## Troubleshooting

### Tenant Not Found

```python
# Error: TenantNotFound exception
# Solution: Verify domain mapping
from django_omnitenant.utils import get_domain_model

Domain = get_domain_model()
# Check domain exists
print(Domain.objects.all())
```

### Wrong Tenant Data

```python
# Error: Queries return data from wrong tenant
# Solution: Ensure middleware is active
print(request.tenant)  # Should show current tenant

# Or use TenantContext explicitly
from django_omnitenant.tenant_context import TenantContext
tenant = TenantContext.get_tenant()
print(tenant)
```

### Migrations Fail

```bash
# Error: Migration fails for specific tenant
# Solution: Run with verbose output
python manage.py migratetenant --tenant-id=acme --verbosity=2

# Or run step by step
python manage.py migratetenant --tenant-id=acme --plan
```

## Next Steps

- Explore the [API Reference](../api/)
- Check [Management Commands](../api/management_commands/)
- Read [Security Best Practices](../security/)
- Join [Community Discussions](https://github.com/RahulRimal/django-omnitenant/discussions)

