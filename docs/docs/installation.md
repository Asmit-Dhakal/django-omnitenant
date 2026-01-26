---
hide:
  - navigation
---



# Installation

## Overview

This guide covers installing **django-omnitenant** and getting it ready for use in your Django project.

## System Requirements

### Python

- **Python 3.8+** - Required for contextvars support
- **Python 3.9+** - Recommended for best compatibility

Check your Python version:

```bash
python --version
```

### Django

- **Django 3.2+** - LTS version recommended
- **Django 4.0+** - Full support for modern async features

Check your Django version:

```bash
django-admin --version
```

### Database

#### PostgreSQL (Recommended)

- **PostgreSQL 10+** - For schema-per-tenant isolation
- **PostgreSQL 12+** - Recommended for best performance
- **psycopg2-binary 2.8+** - Python PostgreSQL adapter

```bash
psql --version
```

Install psycopg2-binary:

```bash
pip install psycopg2-binary
```

#### Other Databases

While django-omnitenant is optimized for PostgreSQL:

- **MySQL 5.7+** - Partial support (database isolation only)
- **SQLite 3** - Development/testing only (not recommended for production)
- **Oracle** - Roadmap for future support

### Optional Dependencies

#### Celery (For Async Tasks)

For background job processing with tenant awareness:

```bash
pip install celery>=5.0
```

Versions:

- **Celery 5.0+** - Full support
- **Celery 4.4** - Limited support (may have compatibility issues)

#### Redis (For Caching)

For distributed caching with tenant isolation:

```bash
pip install redis>=3.5
```

Versions:

- **Redis 3.5+** - Full support
- **Redis 6.0+** - Recommended for production

Redis server:

```bash
# macOS
brew install redis
redis-server

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# Docker
docker run -d -p 6379:6379 redis:latest
```

#### DRF (Django REST Framework)

For building REST APIs with multi-tenant support:

```bash
pip install djangorestframework>=3.12
```

## Installation Methods

### 1. Via pip (Recommended)

Install from PyPI:

```bash
pip install django-omnitenant
```

Install with optional dependencies:

```bash
# With Celery support
pip install django-omnitenant[celery]

# With Redis caching
pip install django-omnitenant[redis]

# With both
pip install django-omnitenant[celery,redis]

# Full installation (all extras)
pip install django-omnitenant[all]
```

Verify installation:

```bash
python -c "import django_omnitenant; print(django_omnitenant.__version__)"
```

### 2. From Source

For development or latest unreleased features:

```bash
# Clone repository
git clone https://github.com/RahulRimal/django-omnitenant.git
cd django-omnitenant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

Verify development installation:

```bash
python -m django --version
```

### 3. Docker

Using Docker for isolated environment:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "config.wsgi:application"]
```

## Virtual Environment Setup

### Using venv (Built-in)

```bash
# Create virtual environment
python -m venv venv

# Activate
source venv/bin/activate       # macOS/Linux
# or
venv\Scripts\activate          # Windows

# Verify activation
which python                   # Should show path inside venv
```

### Using Poetry

```bash
# Create project with Poetry
poetry new my_project
cd my_project

# Add django-omnitenant
poetry add django-omnitenant django

# Activate virtual environment
poetry shell
```

### Using Conda

```bash
# Create environment
conda create -n django_env python=3.10 postgresql

# Activate
conda activate django_env

# Install django-omnitenant
pip install django-omnitenant
```

## Django Project Setup

### 1. Create Django Project

If you don't have an existing Django project:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install Django
pip install django

# Create project
django-admin startproject config

# Create app
cd config
python manage.py startapp myapp
```

### 2. Install django-omnitenant

```bash
pip install django-omnitenant psycopg2-binary
```

### 3. Configure Settings

Add to your Django `settings.py`:

```python
# settings.py

# Add to INSTALLED_APPS
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    # Your apps
    'myapp',

    # Add django-omnitenant
    'django_omnitenant',
]

# Add middleware (early in list)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Add tenant middleware
    'django_omnitenant.middleware.TenantMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Add database router
DATABASE_ROUTERS = [
    'django_omnitenant.routers.TenantRouter',
]

# Configure omnitenant
OMNITENANT_CONFIG = {
    'TENANT_MODEL': 'myapp.Tenant',
    'DOMAIN_MODEL': 'myapp.Domain',
    'PUBLIC_HOST': 'localhost:8000',
    'PUBLIC_TENANT_NAME': 'public',
    'MASTER_TENANT_NAME': 'master',
    'TENANT_RESOLVER': 'django_omnitenant.resolvers.CustomDomainTenantResolver',
}
```

### 4. Create Tenant Models

Create models in `myapp/models.py`:

```python
from django.db import models
from django_omnitenant.models import BaseTenant, BaseDomain

class Tenant(BaseTenant):
    """Custom tenant model."""
    description = models.TextField(blank=True)
    max_users = models.IntegerField(default=10)
    
    def __str__(self):
        return self.name

class Domain(BaseDomain):
    """Custom domain model."""
    pass
```

### 5. Run Migrations

```bash
# Create and run migrations
python manage.py makemigrations
python manage.py migrate
```

### 6. Verify Installation

```bash
# Run Django shell
python manage.py shell

# Inside shell
>>> from django_omnitenant.utils import get_tenant_model
>>> Tenant = get_tenant_model()
>>> print(Tenant)
<class 'myapp.models.Tenant'>
```

## Database Configuration

### PostgreSQL Setup (Recommended)

#### Local Development

```bash
# Create PostgreSQL user
createuser -P django_user
# Enter password when prompted

# Create database
createdb -O django_user django_omnitenant_db

# Verify connection
psql -h localhost -U django_user -d django_omnitenant_db
```

Configure in `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'django_omnitenant_db',
        'USER': 'django_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

#### With Docker

```bash
# Start PostgreSQL container
docker run -d \
  --name postgres \
  -e POSTGRES_USER=django_user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=django_omnitenant_db \
  -p 5432:5432 \
  postgres:14

# Verify
docker exec postgres psql -U django_user -d django_omnitenant_db -c "SELECT 1"
```

#### Environment Variables

Store sensitive credentials in `.env`:

```bash
# .env
DB_NAME=django_omnitenant_db
DB_USER=django_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
```

Load in `settings.py`:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}
```

### SQLite Setup (Development Only)

For quick development testing:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

## Cache Configuration

### Redis Setup

Configure Redis cache in `settings.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### Local Cache (Development)

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'django-omnitenant-cache',
    }
}
```

### Dummy Cache (Testing)

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
```

## Celery Configuration (Optional)

### Basic Setup

Create `config/celery.py`:

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

Configure in `settings.py`:

```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Enable omnitenant patches
OMNITENANT_CONFIG = {
    'PATCHES': [
        'django_omnitenant.patches.cache',
        'django_omnitenant.patches.celery',
    ],
}
```

### With Supervisor

Create `/etc/supervisor/conf.d/celery.conf`:

```ini
[program:celery]
command=python manage.py celery worker -l info
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
```

## Verification

### Check Installation

```bash
python manage.py shell
```

Inside shell:

```python
# Verify django-omnitenant
>>> import django_omnitenant
>>> django_omnitenant.__version__
'1.0.0'

# Verify configuration
>>> from django_omnitenant.conf import settings
>>> settings.TENANT_MODEL
'myapp.Tenant'

# Verify models
>>> from django_omnitenant.utils import get_tenant_model
>>> Tenant = get_tenant_model()
>>> Tenant.objects.count()
0
```

### Run Migrations

```bash
python manage.py migrate
```

Expected output:

```
Running migrations:
  Applying django_omnitenant.0001_initial... OK
  Applying myapp.0001_initial... OK
```

### Create First Tenant

```bash
python manage.py createtenant
```

Follow interactive prompts to create your first tenant.

## Troubleshooting Installation

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'django_omnitenant'`

**Solution**: Ensure django-omnitenant is installed:

```bash
pip install django-omnitenant
pip list | grep django-omnitenant
```

### Database Errors

**Error**: `psycopg2.OperationalError: could not connect to server`

**Solution**: Verify PostgreSQL is running and credentials are correct:

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U django_user -d django_omnitenant_db
```

### Migration Errors

**Error**: `django.db.migrations.exceptions.MigrationSchemaMissing`

**Solution**: Run migrations:

```bash
python manage.py migrate
```

### Import Configuration Errors

**Error**: `django.core.exceptions.ImproperlyConfigured`

**Solution**: Check OMNITENANT_CONFIG in settings.py is complete:

```python
OMNITENANT_CONFIG = {
    'TENANT_MODEL': 'myapp.Tenant',
    'DOMAIN_MODEL': 'myapp.Domain',
    'PUBLIC_HOST': 'example.com',
    'TENANT_RESOLVER': 'django_omnitenant.resolvers.CustomDomainTenantResolver',
}
```

### Middleware Issues

**Error**: `TenantMiddleware not applied`

**Solution**: Ensure middleware is in MIDDLEWARE:

```python
MIDDLEWARE = [
    # ... other middleware
    'django_omnitenant.middleware.TenantMiddleware',
    # ... other middleware
]
```

## Next Steps

After successful installation:

1. **Read the [Usage Guide](usage.md)** - Learn how to use django-omnitenant
2. **Configure Your Tenants** - Set up your first tenants
3. **Create Models** - Build your multi-tenant data models
4. **Check the [API Reference](../api/)** - Explore detailed API documentation

## Support

For issues or questions:

- **Documentation**: [Read the Docs](https://django-omnitenant.readthedocs.io/)
- **GitHub Issues**: [Report Issues](https://github.com/RahulRimal/django-omnitenant/issues)
- **Discussions**: [Join Discussions](https://github.com/RahulRimal/django-omnitenant/discussions)
