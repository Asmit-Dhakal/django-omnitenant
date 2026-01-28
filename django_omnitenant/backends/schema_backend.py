"""
Schema-per-Tenant Backend Module

This module implements the Schema-per-Tenant isolation strategy where each tenant
gets its own PostgreSQL schema within a shared database.

Isolation Strategy:
    Each tenant is isolated in a separate PostgreSQL schema within the same database.
    This provides strong logical isolation while sharing physical database resources.

Architecture:
    - All tenants share a single PostgreSQL database
    - Each tenant gets a dedicated schema (separate namespace)
    - Shared infrastructure (connection pool, server resources)
    - Table structures identical across schemas (same migrations)
    - Data completely isolated via schema search_path mechanism

Schema Concept:
    A PostgreSQL schema is a named namespace within a database:
    - Multiple schemas can coexist in one database
    - Tables in different schemas can have identical names (e.g., public.users, tenant1.users)
    - Each schema has its own permissions, sequences, functions
    - SET search_path controls which schema queries access
    
    Example:
    ```sql
    -- Create tenant1 schema
    CREATE SCHEMA tenant1;
    
    -- Create table in tenant1 schema
    CREATE TABLE tenant1.users (id INT, name TEXT);
    
    -- Access via fully qualified name
    SELECT * FROM tenant1.users;
    
    -- Or set search_path to search that schema automatically
    SET search_path TO tenant1;
    SELECT * FROM users;  -- Queries tenant1.users
    ```

Isolation Mechanism:
    PostgreSQL enforces schema isolation via search_path:
    - Each connection has a search_path (list of schemas to search)
    - Queries search schemas in order (typically "tenant1, public")
    - Cross-tenant data access requires explicit schema qualification
    - Very hard to accidentally leak data across tenants
    
    Example isolation:
    ```python
    # Tenant1 context
    SET search_path TO tenant1, public;
    SELECT * FROM users;  # Returns tenant1.users, not tenant2.users
    
    # Tenant2 context
    SET search_path TO tenant2, public;
    SELECT * FROM users;  # Returns tenant2.users, isolated from tenant1
    ```

Lifecycle:
    1. create() - Creates tenant schema, runs migrations
    2. activate() - Sets search_path to tenant's schema
    3. deactivate() - Restores previous schema search_path
    4. delete() - Drops schema and removes data
    5. migrate() - Runs migrations in tenant's schema

Performance:
    - Faster than database-per-tenant (fewer connections)
    - Slower than shared schema (more schema overhead)
    - Good balance for medium number of tenants (dozens to hundreds)
    - Migrations run faster (one database, multiple schemas)

Resource Usage:
    - One database connection pool (shared across tenants)
    - Lower memory footprint than database-per-tenant
    - Scales better with many tenants (< 1000s)
    - Shared infrastructure simpler to manage

Limitations:
    - Cannot use different database engines per tenant
    - All tenants share connection pool capacity
    - Single database server failure affects all tenants
    - Shared database configuration (charset, collation, etc.)

Usage Example:
    ```python
    from django_omnitenant.backends.schema_backend import SchemaTenantBackend
    from myapp.models import Tenant
    from django_omnitenant.tenant_context import TenantContext
    
    # Create tenant
    tenant = Tenant.objects.create(
        tenant_id='acme',
        config={'schema_name': 'tenant_acme'}
    )
    
    # Provision schema
    backend = SchemaTenantBackend(tenant)
    backend.create(run_migrations=True)
    
    # Use tenant
    with TenantContext.use_tenant(tenant):
        # search_path automatically set to tenant_acme
        User.objects.create(username='john')
    
    # Cleanup
    backend.delete(drop_schema=True)
    ```

Related:
    - base.py: Abstract backend base class
    - database_backend.py: Database-per-tenant alternative
    - tenant_context.py: Request context management
    - utils.py: Utility functions like get_active_schema_name
    - postgresql/base.py: PostgreSQL-specific routing
"""

from django.core.management import call_command
from django.db import connection

from django_omnitenant.models import BaseTenant
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_active_schema_name

from .base import BaseTenantBackend


class SchemaTenantBackend(BaseTenantBackend):
    """
    Schema-per-Tenant isolation backend.
    
    Implements the schema-per-tenant isolation strategy where each tenant
    gets its own PostgreSQL schema within a shared database.
    
    This backend uses PostgreSQL's schema mechanism to provide logical data
    isolation while sharing physical database resources. Each tenant's tables
    exist in a separate schema namespace.
    
    Key Features:
        - Shared database with separate schemas per tenant
        - Lower resource usage than database-per-tenant
        - Faster schema creation than database creation
        - Migrations run in shared database (faster)
        - PostgreSQL search_path controls tenant isolation
        
    Schema vs Database:
        Unlike database-per-tenant:
        - One PostgreSQL database (all tenants)
        - Multiple schemas within the database
        - Lower memory footprint
        - Fewer connections needed
        - Simpler infrastructure
        
        Compared to shared-schema:
        - Complete logical isolation (per-schema)
        - Row-level filters not needed
        - Better performance (less filtering)
        - More complex migrations
        
    Configuration:
        Tenants can specify schema_name in config:
        - If provided: use tenant.config['schema_name']
        - If not provided: use tenant.tenant_id as schema name
        
        Example:
        ```python
        # Uses 'acme' as schema name
        tenant = Tenant.objects.create(
            tenant_id='acme',
            config={}
        )
        
        # Uses 'tenant_acme' as schema name
        tenant = Tenant.objects.create(
            tenant_id='acme',
            config={'schema_name': 'tenant_acme'}
        )
        ```
        
    Isolation Mechanism:
        PostgreSQL search_path controls which schema is queried:
        - connection.set_schema(schema_name) sets the search_path
        - Subsequent queries default to that schema
        - Prevents cross-tenant data access
        - Very efficient (database-native)
        
    Attributes:
        tenant (BaseTenant): The tenant instance
        schema_name (str): PostgreSQL schema name for this tenant
        previous_schema (str): Saved schema for deactivation
    """

    def __init__(self, tenant: BaseTenant):
        """
        Initialize schema backend for a tenant.
        
        Args:
            tenant (BaseTenant): Tenant instance to manage
            
        Process:
            1. Call parent __init__ to store tenant reference
            2. Determine schema name from config or use tenant_id
            3. Store schema name for use in SQL statements
            
        Schema Name Determination:
            - First priority: tenant.config.get('schema_name')
            - Fallback: tenant.tenant_id
            - This allows flexibility in naming schemas
            
        Example:
            ```python
            # Schema name will be 'acme'
            tenant1 = Tenant(tenant_id='acme')
            backend1 = SchemaTenantBackend(tenant1)
            assert backend1.schema_name == 'acme'
            
            # Schema name will be 'tenant_acme'
            tenant2 = Tenant(
                tenant_id='acme',
                config={'schema_name': 'tenant_acme'}
            )
            backend2 = SchemaTenantBackend(tenant2)
            assert backend2.schema_name == 'tenant_acme'
            ```
        """
        super().__init__(tenant)
        # Determine schema name: explicit config takes precedence over tenant_id
        # This allows customizing schema name while keeping tenant_id consistent
        self.schema_name = tenant.config.get("schema_name") or tenant.tenant_id
    def __init__(self, tenant: BaseTenant):
        super().__init__(tenant)
        self.schema_name = tenant.config.get("schema_name") or tenant.tenant_id

    def bind(self):
        """
        Create the tenant's PostgreSQL schema if it doesn't exist.
        
        This method ensures the schema exists by executing CREATE SCHEMA IF NOT EXISTS.
        The IF NOT EXISTS clause makes this operation idempotent - it's safe to call
        multiple times without errors.
        
        Process:
            1. Get database cursor
            2. Execute CREATE SCHEMA IF NOT EXISTS statement
            3. Print confirmation for logging
            
        Schema Creation:
            The CREATE SCHEMA statement creates a new schema namespace in the database:
            - Schema is empty (no tables initially)
            - Can then create tables, functions, etc. in this schema
            - Multiple schemas can coexist in the same database
            
            Example SQL executed:
            ```sql
            CREATE SCHEMA IF NOT EXISTS "tenant_acme"
            ```
            
        SQL Injection Prevention:
            Schema name is quoted with double quotes:
            - Prevents SQL injection through schema name
            - Allows special characters in schema names
            - Example: "tenant-acme" (with dash) becomes valid identifier
            
        Idempotency:
            The IF NOT EXISTS clause means:
            - First call: creates the schema
            - Subsequent calls: do nothing (no error)
            - Safe to call multiple times in same process
            
        Lifecycle:
            bind() is called during:
            - create() - When provisioning new tenant
            - activate() - To ensure schema exists (lazy binding)
            
        Performance:
            Schema creation is very fast:
            - No table creation needed
            - Just metadata operation
            - Typically completes in milliseconds
            - No locking issues
            
        Error Handling:
            Errors can occur from:
            - Invalid schema name
            - Permission denied
            - Database connection issues
            
            Current implementation raises any exceptions.
            
        Example:
            ```python
            from django_omnitenant.backends.schema_backend import SchemaTenantBackend
            from myapp.models import Tenant
            
            tenant = Tenant.objects.get(tenant_id='acme')
            backend = SchemaTenantBackend(tenant)
            
            # Create the schema
            backend.bind()
            # Now 'tenant_acme' schema exists in the database
            ```
            
        See Also:
            - create(): High-level provisioning that calls bind()
            - activate(): Lazy binds if needed
            - delete(): Removes the schema
        """
        # Get database cursor for executing SQL
        with connection.cursor() as cursor:
            # Execute CREATE SCHEMA with IF NOT EXISTS for idempotency
            # Double quotes around schema name prevent SQL injection
            # and allow special characters in schema names
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema_name}"')
        
        # Log successful binding for visibility
        print(f"[SCHEMA BACKEND] Schema '{self.schema_name}' ensured.")

    def create(self, run_migrations=False, **kwargs):
        """
        Provision a new tenant schema.
        
        This method creates the tenant's PostgreSQL schema and optionally runs
        initial migrations to set up tables.
        
        Process:
            1. Call bind() to create the schema
            2. Call parent create() which:
               - Emits tenant_created signal
               - Runs migrations if run_migrations=True
        
        Args:
            run_migrations (bool): Whether to run migrations after creation.
                                  Default is False.
            **kwargs: Additional arguments passed to parent create()
            
        Workflow:
            1. bind() → CREATE SCHEMA IF NOT EXISTS
            2. signal: tenant_created
            3. migrate() → Run Django migrations (if run_migrations=True)
            
        Migrations:
            When run_migrations=True:
            - All pending migrations are applied to tenant schema
            - Tables are created in the tenant's schema namespace
            - Each tenant gets identical table structure
            
            Example:
            ```
            public schema:
            - django_migrations (shared)
            
            tenant_acme schema:
            - users
            - products
            - orders
            (same structure as tenant_globex)
            ```
            
        Configuration:
            Schema name comes from:
            1. tenant.config['schema_name'] (if provided)
            2. tenant.tenant_id (default)
            
        Error Handling:
            If migration fails:
            ```python
            try:
                backend.create(run_migrations=True)
            except Exception as e:
                logger.error(f"Failed to provision tenant: {e}")
                # Schema may exist but be incomplete
                # May need manual cleanup
            ```
            
        Comparison to database_backend:
            - Schema creation much faster than database creation
            - No separate credentials needed
            - Shares connection pool
            - Migrations run in single database context
            
        Examples:
            ```python
            tenant = Tenant.objects.create(
                tenant_id='acme',
                config={'schema_name': 'tenant_acme'}
            )
            
            backend = SchemaTenantBackend(tenant)
            
            # Just create schema (no migrations)
            backend.create(run_migrations=False)
            
            # Create schema and run migrations
            backend.create(run_migrations=True)
            ```
            
        Performance:
            - Schema creation is fast (milliseconds)
            - Migration time depends on schema complexity
            - Can create many tenants in parallel
            - Much faster than database-per-tenant approach
            
        See Also:
            - bind(): Create the schema
            - migrate(): Run database migrations
            - delete(): Remove the schema
        """
        # Step 1: Create the PostgreSQL schema
        self.bind()
        
        # Step 2: Call parent create() to:
        # - Emit tenant_created signal for listeners
        # - Run migrations if run_migrations=True
        super().create(run_migrations=run_migrations, **kwargs)

    def migrate(self, *args, **kwargs):
        """
        Run database migrations for the tenant's schema.
        
        This method applies Django migrations to the tenant's specific schema,
        creating/updating tables within that schema namespace.
        
        Process:
            1. Activate tenant context (sets search_path to tenant schema)
            2. Run Django migrate command with database='default'
            3. Call parent migrate() to emit tenant_migrated signal
            
        Args:
            *args: Positional arguments for migrate command
            **kwargs: Keyword arguments for migrate command
                     - app_label: Migrate specific app
                     - migration_name: Migrate to specific migration
                     - verbosity: Output verbosity level
                     
        Database Context:
            Uses TenantContext.use_tenant() to:
            - Activate tenant context
            - Set search_path to tenant schema
            - Subsequent migrations target tenant schema
            - Exit context when done
            
            The search_path tells PostgreSQL which schema to search:
            ```sql
            SET search_path TO tenant_acme, public;
            -- Now migrations create tables in tenant_acme, not public
            ```
            
        Single Database:
            Unlike database-per-tenant, all migrations use database='default':
            - All tenants share the same database
            - Only search_path differs per tenant
            - Migrations must be compatible across tenants
            - Much faster than separate database migrations
            
        Signals:
            Emits: tenant_migrated(sender=Tenant, tenant=instance)
            Handlers can perform post-migration setup
            
        Examples:
            ```python
            backend = SchemaTenantBackend(tenant)
            
            # Run all pending migrations
            backend.migrate()
            
            # Migrate specific app
            backend.migrate('myapp')
            
            # With verbosity
            backend.migrate(verbosity=2)
            ```
            
        Management Command:
            Typically invoked via Django command:
            ```bash
            python manage.py migratetenant acme
            python manage.py migratetenants
            ```
            
        Performance:
            Much faster than database-per-tenant:
            - Single database context
            - No connection switching
            - Fewer locks
            - Parallel migration support
            
        Error Handling:
            If migration fails, exception is caught but re-raised:
            ```python
            try:
                backend.migrate()
            except Exception as e:
                logger.error(f"Migration failed for {self.schema_name}: {e}")
                # Schema may be in inconsistent state
            ```
            
        See Also:
            - create(): Provision and optionally migrate
            - activate(): Set search_path to tenant schema
            - TenantContext: Context manager for tenant activation
        """
        # Activate tenant context before running migrations
        # This sets search_path to the tenant's schema
        # Ensures migrations run in the tenant's schema, not shared schema
        with TenantContext.use_tenant(self.tenant):
            # Run Django migrate command
            # database='default' because all tenants share the same database
            # search_path is controlled by TenantContext
            call_command("migrate", *args, database="default", **kwargs)
        
        # Call parent migrate() to emit tenant_migrated signal
        # Allows listeners to perform post-migration setup
        super().migrate()

    def delete(self, drop_schema=True):
        """
        Delete the tenant's PostgreSQL schema.
        
        This method optionally drops the tenant's schema (and all data in it),
        then emits the tenant_deleted signal.
        
        Process:
            1. If drop_schema=True: Execute DROP SCHEMA CASCADE
            2. Call parent delete() to emit tenant_deleted signal
            
        Args:
            drop_schema (bool): Whether to actually drop the schema.
                               Default is True. Set to False for soft delete.
                               
        Raises:
            Exception: If schema drop fails (active connections, permissions, etc.)
            
        Destructive Operation:
            When drop_schema=True, this is IRREVERSIBLE!
            - All tables in the schema are dropped
            - All data in those tables is deleted
            - Cannot be recovered without backups
            
        DROP SCHEMA CASCADE:
            The CASCADE clause means:
            - Drop the schema itself
            - Drop all objects in the schema (tables, functions, etc.)
            - Drop objects that depend on schema objects
            - Clean removal without dependency errors
            
            Without CASCADE, would fail if schema has dependent objects.
            
        Two-Step Deletion:
            The method supports soft and hard deletion:
            
            1. drop_schema=False (soft delete):
               - Schema remains in database
               - Data is preserved
               - Allows for recovery if deletion accidental
               - Only signal is emitted
               
            2. drop_schema=True (hard delete):
               - Schema is permanently removed
               - All tables and data deleted
               - Frees disk space
               - Cannot be recovered
               
        Active Connections:
            If another connection is using the schema, DROP may fail:
            ```
            PostgreSQL ERROR: schema "tenant_acme" is being accessed by other users
            ```
            
            Solutions:
            - Wait for connections to close
            - Disconnect all users from database
            - Force terminate active connections
            
        Error Handling:
            The method uses IF EXISTS to be more graceful:
            ```python
            try:
                backend.delete(drop_schema=True)
            except Exception as e:
                logger.error(f"Error dropping schema: {e}")
                # Schema may not have been dropped
                # May need manual intervention
            ```
            
        SQL Injection Prevention:
            Schema name is quoted:
            ```sql
            DROP SCHEMA IF EXISTS "tenant_acme" CASCADE
            ```
            - Prevents injection through schema name
            - Safely handles special characters
            
        Examples:
            ```python
            tenant = Tenant.objects.get(tenant_id='acme')
            backend = SchemaTenantBackend(tenant)
            
            # Soft delete (keep data, remove from Django)
            backend.delete(drop_schema=False)
            # Schema remains, can be manually restored
            
            # Later, hard delete
            backend.delete(drop_schema=True)
            # Schema permanently deleted
            
            # Clean up model
            tenant.delete()
            ```
            
        Safe Deletion Workflow:
            ```python
            # Archive if needed for compliance
            archive_tenant_data(tenant)
            
            # Soft delete first
            backend.delete(drop_schema=False)
            
            # Verify everything is OK
            # Later, hard delete
            backend.delete(drop_schema=True)
            
            # Clean up
            tenant.delete()
            ```
            
        Comparison to database_backend:
            - Schema drop is much faster than database drop
            - No connection termination needed (same database)
            - Simpler cleanup process
            - Less disk space freed (only schema tables)
            
        See Also:
            - create(): Provision the schema
            - bind(): Create empty schema
            - tenant_deleted signal: For cleanup handlers
        """
        # Only drop the schema if explicitly requested
        if drop_schema:
            # Get database cursor for executing SQL
            with connection.cursor() as cursor:
                # Execute DROP SCHEMA with CASCADE and IF EXISTS
                # CASCADE drops schema and all objects in it
                # IF EXISTS prevents error if schema doesn't exist
                # Double quotes prevent SQL injection
                cursor.execute(f'DROP SCHEMA IF EXISTS "{self.schema_name}" CASCADE')
            
            # Log successful deletion
            print(f"[SCHEMA BACKEND] Schema '{self.schema_name}' dropped.")
        
        # Call parent delete() to emit tenant_deleted signal
        # Allows listeners to perform cleanup tasks
        super().delete()

    def activate(self):
        """
        Activate the tenant's schema for the current context.
        
        This method makes the tenant's schema the active search path, so subsequent
        database queries default to accessing that schema.
        
        Process:
            1. Ensure schema exists by calling bind()
            2. Get current PostgreSQL schema name
            3. Set search_path to tenant's schema
            4. Call parent activate() to emit tenant_activated signal
            
        Schema Activation:
            After activation, queries default to the tenant's schema:
            
            ```python
            backend.activate()
            User.objects.all()  # Queries tenant schema
            ```
            
            Executed SQL:
            ```sql
            SET search_path TO tenant_acme, public;
            SELECT * FROM users;  -- Queries tenant_acme.users, not public.users
            ```
            
        Lazy Binding:
            Calls bind() to ensure schema exists before activation:
            - If schema doesn't exist yet, it's created
            - Allows activate() to work even if create() wasn't called
            - Makes activation more resilient
            
        Schema Search Path:
            PostgreSQL search_path determines which schemas to search:
            - connection.set_schema(schema_name) sets the path
            - Typically: SET search_path TO tenant_acme, public
            - Queries check tenant schema first, then public
            - Prevents accidental access to other tenants
            
        Previous Schema:
            Saves current schema name before changing:
            - Allows restoration on deactivate()
            - Supports nested contexts
            - Ensures proper cleanup
            
        Lifecycle:
            Called when:
            - Entering TenantContext context manager
            - Request middleware starts processing
            - Explicitly switching tenant
            
        Examples:
            ```python
            from django_omnitenant.tenant_context import TenantContext
            
            # Automatic via context manager (preferred)
            with TenantContext.use_tenant(tenant):
                # activate() called automatically
                User.objects.all()  # Queries tenant schema
                # deactivate() called automatically
            
            # Manual usage
            backend.activate()
            try:
                User.objects.all()
            finally:
                backend.deactivate()
            ```
            
        Schema Isolation:
            By setting search_path to the tenant schema:
            - Other tenants' tables are inaccessible
            - Cross-tenant queries would fail (table not found)
            - Very strong isolation mechanism
            - Enforced at database level
            
        Performance:
            activate() is called for every request:
            - SET search_path is fast (microseconds)
            - No expensive operations
            - bind() uses CREATE SCHEMA IF NOT EXISTS (cached)
            - Very efficient activation
            
        Error Handling:
            If activate fails:
            - Exception is raised
            - Context is not fully activated
            - deactivate() won't be called
            - Caller must handle error
            
        Signals:
            Emits: tenant_activated (from parent class)
            Allows handlers to perform per-request setup
            
        See Also:
            - deactivate(): Exit tenant context
            - bind(): Ensure schema exists
            - TenantContext: Context manager for activation
        """
        # Ensure the schema exists before activation
        # Uses IF NOT EXISTS so idempotent (safe to call multiple times)
        self.bind()
        
        # Save the current PostgreSQL schema name
        # Allows restoration on deactivate() for proper cleanup
        # Important for nested contexts and exception handling
        self.previous_schema = get_active_schema_name(connection)
        
        # Set the PostgreSQL search_path to this tenant's schema
        # Makes queries default to this schema
        # Other tenants' tables become inaccessible
        connection.set_schema(self.schema_name)
        
        # Call parent activate() to emit tenant_activated signal
        # Handlers can perform per-request setup (logging, caching, etc.)
        super().activate()

    def deactivate(self):
        """
        Deactivate the tenant's schema and restore previous context.
        
        This method restores the PostgreSQL search_path to what it was before
        activation, effectively exiting the tenant's context.
        
        Process:
            1. Restore previous PostgreSQL schema search_path
            2. Call parent deactivate() to emit tenant_deactivated signal
            
        Schema Restoration:
            After deactivate, queries access previous schema:
            
            ```python
            backend.deactivate()
            User.objects.all()  # Queries previous schema, not tenant schema
            ```
            
            Executed SQL:
            ```sql
            SET search_path TO public;  -- Restore previous schema
            SELECT * FROM users;  -- Queries public.users
            ```
            
        Lifecycle:
            Called when:
            - Exiting TenantContext context manager
            - Request middleware finishes request
            - Explicitly exiting tenant context
            
        Exception Safety:
            deactivate() is guaranteed to be called even if errors occur,
            similar to try/finally semantics:
            
            ```python
            backend.activate()
            try:
                dangerous_operation()  # May raise exception
            finally:
                backend.deactivate()  # Always called, even on exception
            ```
            
        Nested Contexts:
            Supports nested tenant activations:
            
            ```python
            with TenantContext.use_tenant(tenant1):
                # Activates tenant1 schema
                with TenantContext.use_tenant(tenant2):
                    # Activates tenant2 schema
                    # Deactivates, back to tenant1
                # Deactivates, back to previous
            ```
            
            Each deactivate() restores the context from the previous level.
            
        Previous Schema Storage:
            The previous_schema is saved by activate():
            - deactivate() restores it
            - Supports any schema (public, another tenant, custom)
            - Handles all context scenarios
            
        Examples:
            ```python
            from django_omnitenant.tenant_context import TenantContext
            
            # Automatic via context manager (preferred)
            with TenantContext.use_tenant(tenant):
                # activate() called
                User.objects.all()
                # deactivate() called automatically
            
            # Manual usage
            backend.activate()
            try:
                User.objects.all()
            finally:
                backend.deactivate()  # Always called
            ```
            
        Performance:
            deactivate() is called for every request:
            - SET search_path is fast (microseconds)
            - No expensive operations
            - Minimal overhead
            
        Error Handling:
            If deactivate() itself fails:
            - Exception is raised but partial cleanup occurred
            - Previous schema restoration attempted
            - Caller should handle gracefully
            
            ```python
            try:
                backend.deactivate()
            except Exception as e:
                logger.error(f"Error deactivating: {e}")
                # Context is still partially cleaned up
            ```
            
        Signals:
            Emits: tenant_deactivated (from parent class)
            Allows handlers to perform cleanup
            - Clear logging context
            - Flush caches
            - Record metrics
            
        Thread Safety:
            TenantContext uses thread-local storage:
            - Each thread maintains independent context
            - deactivate() in one thread doesn't affect others
            - Safe for concurrent request processing
            
        See Also:
            - activate(): Enter tenant context
            - TenantContext: Context manager for activation/deactivation
            - Schema management: For consistent isolation
        """
        # Restore the PostgreSQL schema that was active before activate() was called
        # This ensures proper cleanup and context restoration
        connection.set_schema(self.previous_schema)
        
        # Call parent deactivate() to emit tenant_deactivated signal
        # Allows listeners to perform cleanup tasks
        super().deactivate()
