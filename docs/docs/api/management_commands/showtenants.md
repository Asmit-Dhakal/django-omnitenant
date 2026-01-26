# Show Tenants Command

`python manage.py showtenants [--isolation-type=<type>] [--format=<format>]`

## Overview

Lists all tenants in the system with details about their configuration and isolation strategy.

## Purpose

Provides visibility into multi-tenant infrastructure:
- View all configured tenants
- Check isolation types
- Export tenant data
- Monitor tenant status
- Audit tenant configuration

## Usage

### Basic Usage

```bash
python manage.py showtenants
```

Displays all tenants in table format.

### Filter by Isolation Type

```bash
python manage.py showtenants --isolation-type=database
python manage.py showtenants --isolation-type=schema
python manage.py showtenants --isolation-type=table
python manage.py showtenants --isolation-type=cache
```

### Export Formats

```bash
# Table format (default)
python manage.py showtenants --format=table

# JSON format
python manage.py showtenants --format=json

# CSV format
python manage.py showtenants --format=csv
```

## Output Formats

### Table Format (Default)

```bash
$ python manage.py showtenants
╔═══════════════╦══════════════════════╦════════════════╦══════════════╗
║ Tenant ID     ║ Name                 ║ Isolation Type ║ Created At   ║
╠═══════════════╬══════════════════════╬════════════════╬══════════════╣
║ acme          ║ ACME Corporation     ║ DATABASE       ║ 2024-01-15   ║
║ globex        ║ Globex Inc           ║ SCHEMA         ║ 2024-01-16   ║
║ dev           ║ Development Tenant   ║ TABLE          ║ 2024-01-17   ║
║ staging       ║ Staging Environment  ║ CACHE          ║ 2024-01-18   ║
╚═══════════════╩══════════════════════╩════════════════╩══════════════╝
```

### JSON Format

```bash
$ python manage.py showtenants --format=json
[
  {
    "tenant_id": "acme",
    "name": "ACME Corporation",
    "isolation_type": "DATABASE",
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "tenant_id": "globex",
    "name": "Globex Inc",
    "isolation_type": "SCHEMA",
    "created_at": "2024-01-16T11:45:00Z"
  }
]
```

### CSV Format

```bash
$ python manage.py showtenants --format=csv
tenant_id,name,isolation_type,created_at
acme,ACME Corporation,DATABASE,2024-01-15T10:30:00Z
globex,Globex Inc,SCHEMA,2024-01-16T11:45:00Z
```

## Filtering

### By Isolation Type

Database isolation tenants:
```bash
python manage.py showtenants --isolation-type=database
```

Schema isolation tenants:
```bash
python manage.py showtenants --isolation-type=schema
```

Table isolation tenants:
```bash
python manage.py showtenants --isolation-type=table
```

Cache isolation tenants:
```bash
python manage.py showtenants --isolation-type=cache
```

### Invalid Type

```bash
$ python manage.py showtenants --isolation-type=invalid
Error: Invalid isolation type.
Valid options: DATABASE, SCHEMA, TABLE, CACHE
```

## Export Uses

### Backup Configuration

```bash
# Export all tenants
python manage.py showtenants --format=json > tenants_backup.json

# Export database tenants
python manage.py showtenants --isolation-type=database --format=csv > db_tenants.csv
```

### Monitor Tenants

```bash
# Check all tenants
python manage.py showtenants

# Regular status checks
# Add to monitoring/alerting system
```

### Reporting

```bash
# Generate report
python manage.py showtenants --format=json | jq 'length'
# Shows total number of tenants

# Count by isolation type
python manage.py showtenants --format=json | jq 'group_by(.isolation_type)'
```

## Isolation Types Explained

### DATABASE
- Separate PostgreSQL database per tenant
- Complete data separation
- Highest isolation level
- Highest resource usage

### SCHEMA
- PostgreSQL schemas in shared database
- Good balance of isolation and resources
- Shared infrastructure
- Moderate isolation

### TABLE
- Row-level separation in shared schema
- Most resource efficient
- Requires careful query construction
- Requires tenant_id filtering

### CACHE
- Cache key prefixing per tenant
- Works with shared cache infrastructure
- Data isolated via key prefixes
- Lightweight isolation

## Examples

### List All Tenants

```bash
$ python manage.py showtenants
Total tenants: 4
```

### Count Database Tenants

```bash
$ python manage.py showtenants --isolation-type=database
Total database isolation tenants: 2
```

### Export for Documentation

```bash
python manage.py showtenants --format=json > docs/tenants.json

python manage.py showtenants --format=csv > reports/tenant_audit.csv
```

### Monitor in Script

```bash
#!/bin/bash
python manage.py showtenants --format=json | \
  jq '.[] | select(.isolation_type=="DATABASE")' | \
  wc -l
```

## No Tenants

If no tenants exist:

```bash
$ python manage.py showtenants
No tenants found.
```

Create first tenant:
```bash
python manage.py createtenant
```

## Integration

### With Other Tools

```bash
# Count tenants
python manage.py showtenants --format=json | jq 'length'

# Filter by name
python manage.py showtenants --format=json | jq '.[] | select(.name | contains("ACME"))'

# Find tenant by ID
python manage.py showtenants --format=json | jq '.[] | select(.tenant_id=="acme")'
```

### Automation

```bash
# Cron job for regular reports
0 9 * * MON python manage.py showtenants --format=csv > /var/reports/tenants_$(date +\%Y\%m\%d).csv

# Slack notification
python manage.py showtenants --format=json | \
  curl -X POST -d @- https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

## Related Commands

- `createtenant` - Create new tenant
- `migratetenant` - Run migrations for tenant
- `migratealltenants` - Run migrations for all tenants
- `createtenantsuperuser` - Create admin user
- `shell` - Django shell with tenant context
