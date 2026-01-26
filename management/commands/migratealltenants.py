"""
Run Database Migrations for All Tenants

Django management command for bulk executing schema/database migrations across all tenants.

Purpose:
    Simplifies deployment process by running migrations for every tenant in a single
    command invocation. Useful for updating all tenant databases/schemas when deploying
    new application versions with model changes.
    
Key Features:
    - No arguments required (operates on all tenants)
    - Automatically discovers all tenants from database
    - Iterates through each tenant and runs migrations
    - Proper error handling (one tenant's failure doesn't stop others)
    - Detailed per-tenant output for troubleshooting
    - Uses tenant-specific backend for each tenant
    
Use Cases:
    - Production deployments: Run all migrations after code update
    - Multi-tenant applications: Keep all tenants in sync
    - Schema updates: Propagate schema changes to all tenants
    - Initial setup: Migrate all tenants after creating multiple tenants
    
Tenant Isolation Context:
    Each tenant migrated within isolated context:
    - Database-per-tenant: Each tenant's database receives migrations
    - Schema-per-tenant: Each tenant's schema receives migrations
    - Row-level isolation: Migrations run on shared database (once)
    - All tenants independently updated or failed tracked
    
Usage:
    ```bash
    # Migrate all tenants at once
    python manage.py migratealltenants
    
    # Verbose output
    python manage.py migratealltenants --verbosity=2
    ```
    
Command Flow:
    1. Get Tenant model from settings
    2. Query database for all tenant instances
    3. For each tenant:
        a. Retrieve tenant-specific backend
        b. Execute backend.migrate()
        c. Output success or error
    4. Continue to next tenant even if one fails
    5. Provide summary of migrations
    
Error Handling:
    - Individual tenant failures caught and reported
    - Command continues to migrate other tenants
    - Failed tenants listed in output
    - No global rollback (per-tenant isolation)
    - Exception details shown for each failure

Related:
    - migratetenant: Migrate specific tenant
    - createtenant: Create new tenant
    - TenantBackend: Handles migration execution

Notes:
    - Does not take tenant_id argument (all tenants)
    - Supports standard Django options (verbosity, etc.)
    - Better for production than running migratetenant multiple times
    - Ensures all tenants remain schema-synchronized
"""

from django.core.management.base import BaseCommand

from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_backend, get_tenant_model


class Command(BaseCommand):
    """
    Management command for running migrations on all tenants.
    
    This command provides a convenient way to run migrations across an entire
    multi-tenant deployment without needing to specify each tenant individually.
    It iterates through all tenants, runs their migrations, and handles errors
    gracefully to ensure failures don't stop the migration of other tenants.
    
    Inheritance:
        Inherits from django.core.management.base.BaseCommand, the base Django
        management command class.
    
    Key Functionality:
        - Discovers all tenants from database
        - Runs migrations for each tenant sequentially
        - Catches exceptions per-tenant to continue with others
        - Provides detailed output per tenant
        - Uses tenant-specific backend for each tenant
    
    Attributes:
        help (str): Help text shown in management command listing
    
    Usage Examples:
        Migrate all tenants:
        ```bash
        $ python manage.py migratealltenants
        Migrating tenant: acme
        Tenant 'acme' migrated successfully.
        Migrating tenant: beta
        Tenant 'beta' migrated successfully.
        Migrating tenant: gamma
        Tenant 'gamma' migrated successfully.
        ```
        
        With verbose output:
        ```bash
        $ python manage.py migratealltenants --verbosity=2
        Migrating tenant: acme
        Operations to perform:
          Apply all migrations: ...
        Running migrations:
          Rendering model states... DONE
          Applying app1.0001_initial... OK
          ...
        Tenant 'acme' migrated successfully.
        ...
        ```
    
    Notes:
        - No tenant_id argument (unlike migratetenant command)
        - Useful for deployments when schema changes affect all tenants
        - Each tenant migrated independently (one failure doesn't block others)
        - Takes longer than single migratetenant on large deployments
        - Consider testing on subset first with migratetenant before running on all
    """
    help = "Run migrations for all tenants."

    def handle(self, *args, **options):
        """
        Execute database migrations for all tenants.
        
        This method performs the following steps:
        1. Gets the Tenant model class
        2. Queries database for all tenant instances
        3. Iterates through each tenant sequentially
        4. For each tenant: Gets backend and runs migrations
        5. Catches and reports errors per-tenant
        6. Continues to next tenant even if current one fails
        
        The command provides detailed output for each tenant so administrators
        can identify which tenants succeeded and which failed.
        
        Arguments:
            *args: Positional arguments (typically empty, not used)
            **options (dict): Command options including:
                - verbosity (int): Output verbosity level (0-3, default 1)
                - no_color (bool): Whether to disable colored output
                - [other options]: Standard Django command options
        
        Returns:
            None: Django management commands don't return values. Output via stdout/stderr.
        
        Process Flow:
            ```
            1. Get Tenant model
                Tenant = get_tenant_model()
            
            2. Query all tenants
                for tenant in Tenant.objects.all():
                    # Process each tenant
            
            3. For each tenant:
                a. Output migration start message
                   self.stdout.write(
                       self.style.MIGRATE_HEADING(f'Migrating tenant: {tenant_id}')
                   )
                
                b. Get tenant-specific backend
                   backend = get_tenant_backend(tenant)
                
                c. Execute migrations
                   backend.migrate()
                
                d. Output success
                   self.stdout.write(
                       self.style.SUCCESS(f'Tenant {tenant_id} migrated successfully.')
                   )
            
            4. On exception:
                except Exception as e:
                    # Log error but continue to next tenant
                    self.stdout.write(
                        self.style.ERROR(f'Migrations failed for {tenant_id}: {e}')
                    )
            ```
        
        Usage Examples:
            Basic migration of all tenants:
            ```bash
            $ python manage.py migratealltenants
            Migrating tenant: acme
            Tenant 'acme' migrated successfully.
            Migrating tenant: beta
            Tenant 'beta' migrated successfully.
            Migrating tenant: gamma
            Tenant 'gamma' migrated successfully.
            ```
            
            With verbosity for debugging:
            ```bash
            $ python manage.py migratealltenants --verbosity=2
            Migrating tenant: acme
            Operations to perform:
              Apply all migrations: app1, app2, ...
            Running migrations:
              Rendering model states... DONE (5.234s)
              Applying app1.0001_initial... (0.234s)
              Applying app1.0002_add_field... (0.105s)
              Applying app2.0001_initial... (0.187s)
              ...
            Tenant 'acme' migrated successfully.
            
            Migrating tenant: beta
            [...migrations for beta...]
            Tenant 'beta' migrated successfully.
            
            [...more tenants...]
            ```
            
            With partial failure:
            ```bash
            $ python manage.py migratealltenants
            Migrating tenant: acme
            Tenant 'acme' migrated successfully.
            Migrating tenant: beta
            Migrations failed for tenant 'beta': IntegrityError: duplicate key value
            Migrating tenant: gamma
            Tenant 'gamma' migrated successfully.
            # Note: beta failed, but acme and gamma succeeded
            ```
        
        Error Handling:
            
            Case 1: Migration syntax error in migration file
            ```bash
            $ python manage.py migratealltenants
            Migrating tenant: acme
            Migrations failed for tenant 'acme': ImportError: cannot import name 'SomeModel'
            # Continues to next tenant despite error
            ```
            
            Case 2: Database connection error for specific tenant
            ```bash
            $ python manage.py migratealltenants
            Migrating tenant: acme
            Migrations failed for tenant 'acme': could not connect to database
            # Continues to other tenants
            ```
            
            Case 3: Schema error (e.g., column already exists)
            ```bash
            $ python manage.py migratealltenants
            Migrating tenant: beta
            Migrations failed for tenant 'beta': column already exists
            # Continues despite error
            ```
        
        Important Characteristics:
            - Sequential execution: Tenants migrated one at a time
            - No dependency: One tenant's failure doesn't affect others
            - No rollback: Failed tenants don't rollback successful ones
            - All tenants attempted: Even if some fail, all are tried
            - Detailed output: Each tenant's status clearly shown
        
        Notes:
            - No --tenant-id argument (operates on all)
            - Inherits Django options (--verbosity, --no-color, etc.)
            - Output styled with MIGRATE_HEADING and SUCCESS/ERROR colors
            - Exception details displayed for debugging failures
            - On production, consider dry-run with single migratetenant first
            - Large deployments: may take considerable time if many tenants
        
        Integration Points:
            - Calls get_tenant_model(): Gets configured Tenant model
            - Calls Tenant.objects.all(): Gets all tenant instances
            - Calls get_tenant_backend(): Gets tenant-specific backend
            - Backend.migrate(): Executes migrations in tenant context
            - Uses self.style: Django's output formatting (MIGRATE_HEADING, SUCCESS, ERROR)
            - Uses self.stdout: Django's command output stream
        """
        # Get the Tenant model class (can be customized via settings)
        Tenant = get_tenant_model()

        # Iterate through all tenants in database
        for tenant in Tenant.objects.all():  # type: ignore
            tenant: BaseTenant = tenant
            
            # Display which tenant we're about to migrate (good for monitoring output)
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"Migrating tenant: {tenant.tenant_id}")
            )

            # Try to migrate this tenant, but continue if failure
            try:
                # Get the backend that knows how to access this tenant's database/schema
                backend = get_tenant_backend(tenant)
                
                # Execute migrations for this tenant in its isolated context
                backend.migrate()
                
                # On success, confirm to user
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Tenant '{tenant.tenant_id}' migrated successfully."
                    )
                )
            except Exception as e:
                # On failure, log error but continue to next tenant
                # This ensures one tenant's error doesn't prevent others from migrating
                self.stdout.write(
                    self.style.ERROR(
                        f"Migrations failed for tenant '{tenant.tenant_id}': {e}"
                    )
                )
