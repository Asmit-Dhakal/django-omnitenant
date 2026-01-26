# Migrate Tenant Command

`python manage.py migratetenant --tenant-id=<tenant_id>`

## Overview

Runs database migrations for a specific tenant's database or schema.

## Purpose

Applies Django migrations to a single tenant's isolated database or schema, enabling:
- Per-tenant schema updates
- Controlled migration execution
- Tenant-specific database evolution
- Zero-downtime updates per tenant

## Usage

### Basic Usage

```bash
python manage.py migratetenant --tenant-id=acme
```

### Show Migration Status

```bash
python manage.py migratetenant --tenant-id=acme --plan
```

### Migrate Specific App

```bash
python manage.py migratetenant --tenant-id=acme myapp
```

## Required Arguments

### `--tenant-id` (Required)

Specifies which tenant to migrate:

```bash
python manage.py migratetenant --tenant-id=acme
```

If tenant doesn't exist:
```
Error: Tenant 'acme' does not exist.
Please create one with the tenant id 'acme' first.
```

## Optional Arguments

All Django migrate command arguments supported:

- `app_label` - Migrate specific app only
- `migration_name` - Migrate to specific migration
- `--plan` - Show migration plan without executing
- `--fake` - Mark migration as applied without running
- `--fake-initial` - Fake initial migrations
- `--no-input` - Skip prompts

Examples:

```bash
# Show migration plan
python manage.py migratetenant --tenant-id=acme --plan

# Migrate specific app
python manage.py migratetenant --tenant-id=acme users

# Migrate to specific migration
python manage.py migratetenant --tenant-id=acme users 0002_alter_user_email

# Fake initial migrations
python manage.py migratetenant --tenant-id=acme --fake-initial

# Skip confirmation prompts
python manage.py migratetenant --tenant-id=acme --no-input
```

## Migration Flow

### Single Tenant
```bash
$ python manage.py migratetenant --tenant-id=acme
Running migrations for tenant: ACME Corporation
Operations to perform:
  Apply all migrations: users, products, orders
Running migrations:
  users/0001_initial.py ... OK
  users/0002_alter_user_email.py ... OK
  products/0001_initial.py ... OK
  orders/0001_initial.py ... OK
Migrations completed successfully for tenant 'acme'.
```

### Show Plan
```bash
$ python manage.py migratetenant --tenant-id=acme --plan
Planned operations for tenant 'acme':
  users/0001_initial.py
  users/0002_alter_user_email.py
  products/0001_initial.py
  orders/0001_initial.py
```

## What Happens

1. Validates tenant exists with specified tenant_id
2. Gets tenant backend (database/schema configuration)
3. Sets up tenant's database connection
4. Runs all pending migrations:
   - Creates django_migrations table if needed
   - Applies unapplied migrations
   - Tracks applied migrations
5. Completes with success or error

## Database Isolation

Migrations respect tenant isolation:

**Database Isolation:**
```
Tenant A (acme): acme_db
Tenant B (globex): globex_db

$ migratetenant --tenant-id=acme
# Connects to acme_db
# Runs migrations only on acme_db

$ migratetenant --tenant-id=globex
# Connects to globex_db
# Runs migrations only on globex_db
```

**Schema Isolation:**
```
Shared Database: shared_db
Tenant A (acme): public_acme schema
Tenant B (globex): public_globex schema

$ migratetenant --tenant-id=acme
# Connects to shared_db, schema public_acme
# Runs migrations only in public_acme schema

$ migratetenant --tenant-id=globex
# Connects to shared_db, schema public_globex
# Runs migrations only in public_globex schema
```

## Status Check

Show which migrations are already applied:

```bash
python manage.py migratetenant --tenant-id=acme --plan
```

View migration history:
```bash
python manage.py showmigrations --database=acme
```

## Common Scenarios

### New Tenant Setup
```bash
# Create tenant
python manage.py createtenant

# Run all migrations for new tenant
python manage.py migratetenant --tenant-id=acme
```

### Add New Feature Across All Tenants
```bash
# Run migration on each tenant
python manage.py migratetenant --tenant-id=acme
python manage.py migratetenant --tenant-id=globex
python manage.py migratetenant --tenant-id=dev

# Or use migratealltenants
python manage.py migratealltenants
```

### Rollback Migration
```bash
# Fake a migration to unapply it
python manage.py migratetenant --tenant-id=acme --fake apps/0002_undo_change
```

### Zero-Downtime Updates
```bash
# Migrate one tenant at a time (one per minute)
for tenant_id in acme globex dev staging; do
    python manage.py migratetenant --tenant-id=$tenant_id
    sleep 60
done
```

## Error Handling

### Tenant Not Found
```
Error: Tenant 'unknown' does not exist.
Please create one with the tenant id 'unknown' first.
```
Verify tenant_id is correct and tenant exists.

### Database Connection Failed
```
Error: Cannot connect to tenant database
```
Check database configuration and connectivity.

### Conflicting Migrations
```
Error: Conflicting migrations detected
```
Resolve migration conflicts before applying.

### Permission Denied
```
Error: User does not have permission to create tables
```
Ensure database user has required privileges.

## Performance Tips

- Run on off-peak hours for large migrations
- Use `--plan` to preview before executing
- Monitor migration progress for long-running changes
- Test on staging environment first
- Consider downtime for breaking changes

## Related Commands

- `migratealltenants` - Migrate all tenants
- `createtenant` - Create new tenant
- `showmigrations` - Show migration status
- `makemigrations` - Create new migrations
