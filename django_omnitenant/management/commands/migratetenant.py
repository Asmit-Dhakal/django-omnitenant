"""
Run Database Migrations for a Single Tenant

Django management command for executing schema/database migrations within tenant context.

Purpose:
    Extends Django's migrate command to work with multi-tenant architecture, allowing
    execution of database schema migrations for a specific tenant. Essential for updating
    tenant's database schema when application models change.
    
Key Features:
    - Requires --tenant-id argument to specify target tenant
    - Validates tenant exists before running migrations
    - Uses tenant-specific backend to execute migrations
    - Proper error handling and user feedback
    - Works with all tenant isolation types (database, schema, cache)
    
Tenant Isolation Context:
    Migrations executed within tenant context means:
    - For database-per-tenant: Migrates tenant's specific database
    - For schema-per-tenant: Migrates tenant's specific schema
    - For row-level isolation: Migrations run on shared database
    - All models use tenant's connection/schema automatically
    - Proper isolation ensures schema consistency per tenant
    
Usage:
    ```bash
    # Migrate specific tenant to latest
    python manage.py migratetenant --tenant-id=acme
    
    # Migrate specific app for tenant
    python manage.py migratetenant --tenant-id=acme app_name
    
    # Migrate to specific migration
    python manage.py migratetenant --tenant-id=acme app_name 0002_auto
    
    # Show migration plan without executing
    python manage.py migratetenant --tenant-id=acme --plan
    ```
    
Supported Django Arguments:
    - app_label: Migrate specific app (optional)
    - migration_name: Migrate to specific migration (optional)
    - --plan: Show migration plan without executing
    - --verbosity: Control output verbosity (0-3)
    - --no-color: Disable colored output
    - Any other migrate argument
    
Command Flow:
    1. Parse and extract --tenant-id argument (required)
    2. Retrieve Tenant model from settings
    3. Validate tenant exists in database
    4. Get tenant-specific backend
    5. Call backend.migrate() with tenant context
    6. Backend applies migrations to tenant's database/schema
    7. Output success or error messages
    
Error Handling:
    - CommandError if --tenant-id not provided
    - CommandError if tenant doesn't exist
    - Exception caught and displayed for migration failures
    - Tenant validation prevents migrating non-existent tenants
    - Backend handles database/schema-specific errors

Related:
    - migratealltenants: Migrate all tenants at once
    - createtenant: Create new tenant (needs initial migration)
    - Django's migrate: Parent concept
    - TenantBackend: Handles migration execution per tenant
"""

from django.core.management.base import BaseCommand, CommandError
from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_model
from django_omnitenant.utils import get_tenant_backend


class Command(BaseCommand):
class Command(BaseCommand):
    """
    Management command for running migrations on a specific tenant.
    
    This command extends the Django migrate command to support multi-tenant deployments
    where each tenant may have separate databases or schemas. It wraps the migration
    process to ensure migrations are executed in the proper tenant context.
    
    Inheritance:
        Inherits from django.core.management.base.BaseCommand, the base Django
        management command class.
    
    Key Functionality:
        - Accepts --tenant-id (required) to specify which tenant to migrate
        - Validates tenant exists before attempting migrations
        - Uses TenantBackend to execute migrations in tenant context
        - Handles database/schema-specific migration logic
        - Provides proper error messages for troubleshooting
    
    Attributes:
        help (str): Help text shown in management command listing
    
    Usage Examples:
        Migrate all pending migrations for tenant:
        ```bash
        $ python manage.py migratetenant --tenant-id=acme
        Running migrations for tenant: ACME Corporation
        Applying app1.0001_initial... OK
        Applying app1.0002_add_field... OK
        Migrations completed successfully for tenant 'acme'.
        ```
        
        Migrate specific app:
        ```bash
        $ python manage.py migratetenant --tenant-id=beta app1
        Running migrations for tenant: Beta Corp
        Applying app1.0003_alter_model... OK
        Migrations completed successfully for tenant 'beta'.
        ```
        
        Show migration plan without executing:
        ```bash
        $ python manage.py migratetenant --tenant-id=gamma --plan
        Running migrations for tenant: Gamma Industries
        Planned operations:
        - Apply app1.0001_initial
        - Apply app1.0002_add_field
        ```
    
    Notes:
        - Each tenant can have independent migration state
        - Migration files are shared, but state tracked per tenant
        - Backend handles database/schema routing automatically
        - Essential after deploying application changes to production
    """
    help = "Run migrations for a single tenant."

    def add_arguments(self, parser):
        """
        Add command-line arguments to the command parser.
        
        This method adds the required --tenant-id argument for specifying which
        tenant should be migrated. All other Django migrate arguments are inherited.
        
        Arguments:
            parser (argparse.ArgumentParser): Django's argument parser for this command.
        
        Custom Arguments:
            --tenant-id (str): REQUIRED. Identifier of the specific tenant to migrate.
                If not provided, CommandError is raised. Must reference an existing tenant
                or CommandError is raised in handle().
        
        Django Arguments Inherited (from migrate command):
            app_label: App to migrate (optional, migrates all if not specified)
            migration_name: Specific migration to target (optional)
            --plan: Show migration plan without executing
            --verbosity: Output verbosity (0=silent, 1=normal, 2=verbose, 3=debug)
            --no-color: Disable colored output
            --database: Database alias (less relevant for tenant isolation)
            --skip-checks: Skip system checks
            --no-input: Non-interactive mode
            Any other Django migrate options
        
        Examples:
            ```python
            # Just tenant_id
            $ manage.py migratetenant --tenant-id=acme
            
            # With app filter
            $ manage.py migratetenant --tenant-id=acme users
            
            # With verbosity
            $ manage.py migratetenant --tenant-id=acme --verbosity=2
            
            # Plan only
            $ manage.py migratetenant --tenant-id=acme --plan
            
            # All together
            $ manage.py migratetenant \\
                --tenant-id=acme \\
                users \\
                --verbosity=2 \\
                --no-color
            ```
        
        Notes:
            - Tenant ID is mandatory (no default)
            - Positional app_label is still optional
            - Parser is modified in-place
        """
        parser.add_argument(
            "--tenant-id",
            help="Identifier of the tenant to migrate. "
                 "Required when running this command directly. "
                 "Must be an existing tenant or CommandError will be raised.",
        )

    def handle(self, *args, **options):
        """
        Execute database migrations for the specified tenant.
        
        This method performs the following steps:
        1. Extracts and validates the --tenant-id argument
        2. Retrieves the Tenant model
        3. Validates that the tenant exists
        4. Gets the tenant-specific backend
        5. Calls backend.migrate() to execute migrations
        6. Reports success or failure to user
        
        All migrations are executed within proper tenant context, ensuring that
        schema/database-specific operations target the correct tenant's infrastructure.
        
        Arguments:
            *args: Positional arguments passed to Django's migrate command
                   May include app_label or migration_name
            **options (dict): Command options including:
                - tenant_id (str): Tenant identifier (extracted in this method)
                - verbosity (int): Output verbosity level (default 1)
                - no_color (bool): Whether to disable colored output
                - plan (bool): If True, show plan but don't execute
                - [other migrate options]: Passed to parent migrate command
        
        Returns:
            None: Django management commands don't return values. Output via stdout/stderr.
        
        Process Flow:
            ```
            1. Extract tenant_id from options
                tenant_id = options.pop('tenant_id', None)
                # 'tenant_id': 'acme' or None
            
            2. Validate tenant_id was provided
                if not tenant_id:
                    raise CommandError('--tenant-id is required...')
                # Prevents accidental global migration
            
            3. Get Tenant model class
                Tenant = get_tenant_model()  # e.g., CustomTenant
            
            4. Query for tenant
                tenant = Tenant.objects.get(tenant_id=tenant_id)
                # Raises Tenant.DoesNotExist if not found
            
            5. Confirm to user
                self.stdout.write(
                    self.style.SUCCESS(f'Running migrations for tenant: {tenant}')
                )
            
            6. Get backend for this tenant
                backend = get_tenant_backend(tenant)
                # Backend knows how to access tenant's database/schema
            
            7. Execute migrations via backend
                backend.migrate(*args, **options)
                # Migrations applied to tenant's infrastructure
            
            8. Output success
                self.stdout.write(
                    self.style.SUCCESS('Migrations completed successfully...')
                )
            
            9. On error: catch and display error
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Migrations failed for tenant...: {e}')
                    )
            ```
        
        Usage Examples:
            Migrate tenant with ID 'acme':
            ```bash
            $ python manage.py migratetenant --tenant-id=acme
            Running migrations for tenant: ACME Corporation
            Operations to perform:
              Apply all migrations: ...
            Running migrations:
              Rendering model states... DONE
              Applying app1.0001_initial... OK
              Applying app1.0002_add_field... OK
              ...
            Migrations completed successfully for tenant 'acme'.
            ```
            
            Show migration plan:
            ```bash
            $ python manage.py migratetenant --tenant-id=beta --plan
            Running migrations for tenant: Beta Corp
              Planned operations:
                app1.0001_initial
                app1.0002_add_field
                app2.0005_new_feature
            Migrations completed successfully for tenant 'beta'.
            ```
            
            Verbose output:
            ```bash
            $ python manage.py migratetenant --tenant-id=gamma --verbosity=2
            Running migrations for tenant: Gamma Industries
            Operations to perform:
              Apply all migrations: ...
            Running migrations:
              Rendering model states... DONE (10.234s)
              Applying app1.0001_initial... (time: 0.234s)
              Applying app1.0002_add_field... (time: 0.105s)
              ...
            Migrations completed successfully for tenant 'gamma'.
            ```
        
        Error Handling:
            
            Case 1: --tenant-id not provided
            ```bash
            $ python manage.py migratetenant
            # CommandError: --tenant-id is required when running migrate_tenant directly.
            ```
            
            Case 2: Tenant doesn't exist
            ```bash
            $ python manage.py migratetenant --tenant-id=nonexistent
            # CommandError: Tenant 'nonexistent' does not exist.
            #   Please create one with the tenant id 'nonexistent' first.
            ```
            
            Case 3: Migration error (e.g., syntax error in migration file)
            ```bash
            $ python manage.py migratetenant --tenant-id=acme
            Running migrations for tenant: ACME Corporation
            Migrations failed for tenant 'acme': [error details]
            ```
            
            Case 4: Database connection error
            ```bash
            $ python manage.py migratetenant --tenant-id=acme
            Running migrations for tenant: ACME Corporation
            Migrations failed for tenant 'acme': could not connect to server
            ```
        
        Context Management:
            The backend.migrate() call handles tenant context management:
            - Database-per-tenant: Connects to tenant's specific database
            - Schema-per-tenant: Sets search_path to tenant's schema (PostgreSQL)
            - Row-level isolation: Runs on shared database with row-level filters
            - All ORM queries automatically scoped to tenant
            - No explicit context management needed in this method
        
        Notes:
            - Tenant validation prevents migrating non-existent tenants
            - Each tenant's migration state tracked independently
            - Migration files are shared across all tenants
            - Failed migrations don't affect other tenants
            - Rolling back specific tenant requires manual intervention
            - Check --plan before executing on production
        
        Integration Points:
            - Calls get_tenant_model(): Gets configured Tenant model
            - Calls get_tenant_backend(): Gets tenant-specific backend instance
            - Backend.migrate(): Executes migrations in tenant context
            - Uses self.style: Django's output formatting (SUCCESS, ERROR, WARNING)
            - Uses self.stdout: Django's command output stream
        """
        # Extract tenant_id from options and remove it (backend doesn't know this arg)
        tenant_id = options.pop("tenant_id", None)
        
        # Get the Tenant model class (can be customized via settings)
        Tenant = get_tenant_model()

        # Validate that tenant_id was provided
        if not tenant_id:
            raise CommandError(
                "--tenant-id is required when running migrate_tenant directly. "
                "Usage: python manage.py migratetenant --tenant-id=<tenant_id>"
            )

        # Validate that tenant exists before attempting migrations
        try:
            tenant: BaseTenant = Tenant.objects.get(tenant_id=tenant_id)  # type: ignore
        except Tenant.DoesNotExist:
            raise CommandError(
                f"Tenant '{tenant_id}' does not exist. "
                f"Please create one with the tenant id '{tenant_id}' first "
                f"using: python manage.py createtenant"
            )

        # Confirm to user which tenant we're migrating (good UX, prevents mistakes)
        self.stdout.write(
            self.style.SUCCESS(f"Running migrations for tenant: {tenant}")
        )

        # Execute migrations within tenant context
        try:
            # Get the backend that knows how to access this tenant's database/schema
            backend = get_tenant_backend(tenant)
            
            # Call backend.migrate() to execute migrations in tenant context
            # Backend handles database selection, schema setting, etc.
            backend.migrate(*args, **options)
            
            # On success, confirm completion to user
            self.stdout.write(
                self.style.SUCCESS(
                    f"Migrations completed successfully for tenant '{tenant_id}'."
                )
            )
        except Exception as e:
            # On failure, output error message with details
            # Don't re-raise - allow other tenants to migrate even if one fails
            self.stdout.write(
                self.style.ERROR(f"Migrations failed for tenant '{tenant_id}': {e}")
            )
