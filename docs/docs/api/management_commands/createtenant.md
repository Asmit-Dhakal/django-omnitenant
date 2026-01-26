# Create Tenant Command

`python manage.py createtenant`

## Overview

Interactive command to create new tenants with customizable isolation strategy and database configuration.

## Purpose

Provides a user-friendly interface for creating and initializing new tenants, including:

- Tenant ID and name specification
- Isolation type selection (database, schema, cache)
- Database creation and configuration
- Automatic migration execution

## Usage

### Basic Usage

```bash
python manage.py createtenant
```

The command will prompt for:

1. **Tenant ID** - Unique identifier for the tenant
2. **Tenant Name** - Display name for the tenant
3. **Isolation Type** - Choose database/schema/table/cache isolation
4. **Database Config** (if database isolation) - Connection details
5. **Run Migrations** - Whether to run migrations immediately

### Interactive Prompts

```bash
$ python manage.py createtenant
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

## Isolation Types

### Database Isolation

- Separate PostgreSQL database per tenant
- Each tenant has isolated database instance
- Complete data separation
- Highest isolation level

### Schema Isolation

- PostgreSQL schemas within shared database
- Separate schema per tenant
- Shared database infrastructure
- Good balance of isolation and resource efficiency

### Table Isolation

- Row-level data separation in shared schema
- Tenant_id column for data filtering
- Most resource efficient
- Requires careful query construction

### Cache Isolation

- Cache key prefixing per tenant
- Shared cache infrastructure
- Tenant data isolation via prefixes

## Database Configuration

When selecting database isolation, specify:

- **Database Name** - PostgreSQL database name
- **Database User** - Database user with create permissions
- **Database Password** - User's password
- **Database Host** - Host/IP of database server
- **Database Port** - Port (default: 5432)

Example:

```bash
Enter database name for tenant: client_prod
Enter database user: client_admin
Enter database password: ****
Enter database host: db.example.com
Enter database port (default: 5432): 5432
```

## Migration Execution

After tenant creation, migrations can be run:

```bash
Do you want to run migrations for this tenant now? (y/n): y
```

This executes all pending migrations for the new tenant's database/schema.

## Database Creation

For database isolation, optionally create the database automatically:

```bash
Do you want to create the database now? (y/n): y
```

The command will:

1. Create PostgreSQL database with specified name
2. Create database user with provided credentials
3. Grant necessary permissions
4. Initialize database schema (if migrations run)

## What Happens

1. Tenant object created in master database
2. Tenant stored with:
   - tenant_id: Unique identifier
   - name: Display name
   - isolation_type: Selected strategy
   - config: Database config (if database isolation)
3. Database/schema created (if specified)
4. Migrations executed (if selected)
5. Tenant ready for use

## Output

Successful creation shows:

```
✓ Tenant 'acme' created successfully
✓ Database 'acme_db' created
✓ Migrations completed
Tenant is ready to use
```

## Error Handling

### Duplicate Tenant ID

```
Error: Tenant with ID 'acme' already exists
```

Use unique tenant_id for each tenant.

### Database Connection Failed

```
Error: Cannot connect to database server
```

Verify database host, port, and credentials.

### Invalid Isolation Type

```
Error: Invalid isolation type
Valid options: database, schema, table, cache
```

Choose from available isolation types.

## Related Commands

- `migratetenant` - Run migrations for specific tenant
- `migratealltenants` - Run migrations for all tenants
- `showtenants` - List all tenants
- `createtenantsuperuser` - Create admin user for tenant
- `shell` - Django shell with tenant context
