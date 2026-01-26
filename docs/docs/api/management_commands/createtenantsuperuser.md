# Create Tenant Superuser Command

`python manage.py createtenantsuperuser --tenant-id=<tenant_id>`

## Overview

Creates a Django superuser for a specific tenant with elevated permissions and admin access.

## Purpose

Extends Django's built-in createsuperuser command to work within tenant context, allowing:
- Creation of admin users per tenant
- Superuser privileges within tenant scope
- Proper tenant data isolation
- Django admin access for tenant

## Usage

### Basic Usage

```bash
python manage.py createtenantsuperuser --tenant-id=acme
```

### With Additional Options

```bash
python manage.py createtenantsuperuser \
  --tenant-id=acme \
  --username=admin \
  --email=admin@acme.com \
  --noinput
```

## Required Arguments

### `--tenant-id` (Required)

Specifies which tenant to create superuser for:

```bash
python manage.py createtenantsuperuser --tenant-id=acme
```

If tenant doesn't exist:
```
Error: Tenant with id 'acme' does not exist
```

## Optional Arguments

All Django superuser arguments are supported:

- `--username` - Username for superuser
- `--email` - Email address
- `--no-input` - Non-interactive mode
- `--preserve` - Preserve existing password

Example interactive session:
```bash
$ python manage.py createtenantsuperuser --tenant-id=acme
Using tenant: ACME Corporation
Username: admin
Email address: admin@acme.com
Password: ****
Password (again): ****
Superuser created successfully.
```

## Interactive Mode

When run without `--noinput`, prompts for:

1. **Username** - Unique username for superuser
2. **Email** - Email address
3. **Password** - Secure password (prompted twice for confirmation)

Example:
```bash
$ python manage.py createtenantsuperuser --tenant-id=globex
Using tenant: Globex Corporation
Username: admin
Email address: admin@globex.com
Password: 
Password (again):
Superuser created successfully.
```

## Non-Interactive Mode

For automation, use `--noinput` with all required fields:

```bash
python manage.py createtenantsuperuser \
  --tenant-id=acme \
  --username=admin \
  --email=admin@acme.com \
  --noinput
```

This creates superuser without prompts (password must be set separately).

## What Happens

1. Validates tenant exists with specified tenant_id
2. Sets tenant context for current operation
3. Creates Django User object in tenant's database
4. Marks user as staff and superuser
5. Sets secure password
6. User now has full admin access within tenant

## Tenant Context

The superuser is created in the correct tenant context:

- User created in tenant's database/schema
- User can only access tenant's data
- Admin interface isolated to tenant
- Data cannot be accessed by other tenants

Example:
```bash
# Create admin for acme
python manage.py createtenantsuperuser --tenant-id=acme --username=admin

# Admin can now access:
# - Django admin at /admin/
# - acme's data only
# - Cannot see globex data
```

## Accessing Django Admin

After creating superuser, admin can access:

```
https://acme.example.com/admin/
Username: admin
Password: [password set during creation]
```

Admin sees only:
- ACME tenant's data
- ACME tenant's users/groups
- ACME tenant's configuration

## Error Handling

### Tenant Not Found
```
Error: Tenant with id 'unknown' does not exist
```
Ensure tenant exists with correct tenant_id.

### Username Already Exists
```
Error: User with this username already exists.
```
Choose unique username or delete previous user.

### Invalid Email
```
Error: Enter a valid email address.
```
Provide valid email format.

## Security Considerations

- Superuser has full admin access within tenant
- Password should be strong and secure
- Consider role-based access control for production
- Audit superuser creation and changes
- Use non-interactive mode carefully in CI/CD

## Related Commands

- `createtenant` - Create new tenant
- `migratetenant` - Run migrations for tenant
- `shell` - Django shell with tenant context
- `changepassword` - Change superuser password
