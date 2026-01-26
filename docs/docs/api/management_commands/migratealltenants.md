# Migrate All Tenants Command

`python manage.py migratealltenants`

## Overview

Runs database migrations for all tenants sequentially, ensuring every tenant's database/schema is up-to-date.

## Purpose

Automates migration execution across the entire multi-tenant infrastructure:
- Run migrations on all tenants in one command
- Batch tenant updates
- Ensure consistency across all tenants
- Simplified deployment process

## Usage

### Basic Usage

```bash
python manage.py migratealltenants
```

Runs all pending migrations for every tenant in the system.

## What Happens

1. Gets all Tenant objects from master database
2. For each tenant:
   - Retrieves tenant backend
   - Runs migrations for that tenant
   - Reports success or failure
   - Continues with next tenant
3. Summary of results

## Output Example

```bash
$ python manage.py migratealltenants
Migrating tenant: acme
  users/0001_initial.py ... OK
  users/0002_alter_user_email.py ... OK
✓ Tenant 'acme' migrated successfully.

Migrating tenant: globex
  users/0001_initial.py ... OK
  users/0002_alter_user_email.py ... OK
  products/0001_initial.py ... OK
✓ Tenant 'globex' migrated successfully.

Migrating tenant: dev
  users/0001_initial.py ... OK
✓ Tenant 'dev' migrated successfully.

Migration Summary:
  ✓ acme - migrated successfully
  ✓ globex - migrated successfully
  ✓ dev - migrated successfully
  Total: 3 tenants migrated
```

## Error Handling

Continues with next tenant if one fails:

```bash
Migrating tenant: acme
✓ Tenant 'acme' migrated successfully.

Migrating tenant: globex
✗ Migrations failed for tenant 'globex': Conflicting migrations
Continuing with next tenant...

Migrating tenant: dev
✓ Tenant 'dev' migrated successfully.

Migration Summary:
  ✓ acme - successful
  ✗ globex - FAILED
  ✓ dev - successful
```

### Handle Failures

Tenants with failures should be handled separately:

```bash
# Identify failed tenant
# Fix migration conflict
# Re-run for specific tenant
python manage.py migratetenant --tenant-id=globex
```

## Sequential Execution

Migrations run sequentially (one tenant at a time):

```
Start
  ↓
Migrate acme
  ↓
Migrate globex
  ↓
Migrate dev
  ↓
Complete
```

Benefits:
- Lower resource usage
- Predictable database locks
- Easier debugging
- Reduced connection pool pressure

## Common Scenarios

### Deploy New Feature
```bash
# Make migrations
python manage.py makemigrations

# Run migrations on all tenants
python manage.py migratealltenants

# Verify deployment
python manage.py showtenants
```

### Regular Maintenance
```bash
# Scheduled cron job
0 2 * * * python manage.py migratealltenants >> /var/log/migrations.log 2>&1
```

### Rolling Deployment
```bash
# Option 1: All at once
python manage.py migratealltenants

# Option 2: Staggered
for tenant_id in $(python manage.py showtenants --format=json | jq -r '.[].tenant_id'); do
    python manage.py migratetenant --tenant-id=$tenant_id
    sleep 60  # Wait between tenants
done
```

## Database Isolation

Works correctly with different isolation strategies:

**Database-per-Tenant:**
```
acme_db
  django_migrations table
  user table
  product table

globex_db
  django_migrations table
  user table
  product table

$ migratealltenants
# Migrates each database separately
# Each tracks own migration history
```

**Schema-per-Tenant:**
```
shared_db
  public_acme schema
    django_migrations table
    user table
  public_globex schema
    django_migrations table
    user table

$ migratealltenants
# Migrates each schema separately
# Each schema tracks own migrations
```

## Performance Considerations

### Large Number of Tenants
For 100+ tenants, consider:
- Run during maintenance window
- Monitor disk space (each tenant needs space)
- Monitor database connections
- Use background job queue

### Long-Running Migrations
For migrations taking hours:
- Test on staging first
- Plan maintenance window
- Notify users of potential downtime
- Monitor progress

### Resource Usage
Each migration:
- Uses database connection
- May lock tables
- May use memory
- Sequential execution helps manage load

## Monitoring

### Check Status
```bash
python manage.py showtenants
# Lists all tenants and their status
```

### View Migration History
```bash
# For specific tenant
python manage.py migratetenant --tenant-id=acme --plan

# All tenants
python manage.py showmigrations
```

### Log Output
```bash
# Run with logging
python manage.py migratealltenants 2>&1 | tee migrations.log

# Check for errors
grep ERROR migrations.log
```

## Related Commands

- `migratetenant` - Migrate single tenant
- `showtenants` - List all tenants
- `createtenant` - Create new tenant
- `makemigrations` - Create migration files
- `migrate` - Django's standard migrate command
