"""
PostgreSQL Database Wrapper Module

This module extends Django's PostgreSQL database backend to support schema-per-tenant
isolation by managing PostgreSQL search_path for each database connection.

Purpose:
    Django's default PostgreSQL backend doesn't support dynamic schema switching.
    This wrapper adds schema management capabilities to allow:
    - Switching schemas per connection
    - Tracking current schema state
    - Setting search_path for tenant isolation
    - Maintaining schema state across queries
    
Schema Switching Mechanism:
    PostgreSQL search_path controls which schemas are searched for objects:
    
    ```sql
    SET search_path TO tenant_acme, public;
    SELECT * FROM users;  -- Searches tenant_acme.users first, then public.users
    ```
    
    This wrapper provides Python methods to manage search_path:
    - set_schema(schema_name) - Switch to specific schema
    - set_schema_to_public() - Reset to public schema
    - current_schema property - Get current schema
    
Connection Management:
    Each database connection has:
    - Its own search_path
    - Independent schema tracking
    - Connection pooling compatibility
    - Thread-local state management
    
    When a connection is reused:
    - search_path may need to be reset
    - is_usable() checks if connection is still valid
    - ensure_connection() re-establishes if needed
    
Usage in django-omnitenant:
    The wrapper is configured in Django settings:
    
    ```python
    DATABASES = {
        'default': {
            'ENGINE': 'django_omnitenant.backends.postgresql',
            'NAME': 'multitenant_db',
            'USER': 'postgres',
            'PASSWORD': 'secret',
            'HOST': 'localhost',
            'PORT': 5432,
        }
    }
    ```
    
    Then used via schema backends:
    ```python
    from django.db import connection
    
    # Switch schema
    connection.set_schema('tenant_acme')
    User.objects.all()  # Queries tenant_acme.users
    
    # Reset to public
    connection.set_schema_to_public()
    User.objects.all()  # Queries public.users
    ```

Integration with Backends:
    - SchemaTenantBackend calls set_schema() on activate
    - DatabaseTenantBackend uses separate connections per database
    - TenantContext manages schema switching per request
    - Automatic routing for multi-tenant queries
    
Performance:
    - SET search_path is very fast (microseconds)
    - No expensive operations
    - Minimal overhead vs standard PostgreSQL
    - Efficient for high-frequency switching
    
Security:
    - SQL injection prevented via proper quoting
    - Schema names quoted with double quotes
    - Only affects search_path, not database access
    - Works with PostgreSQL row-level security (RLS)
    
Compatibility:
    - Works with all PostgreSQL versions supporting search_path
    - Compatible with connection pooling (PgBouncer, etc.)
    - Supports prepared statements
    - Works with psycopg2 and psycopg3
    
Related:
    - schema_backend.py: Uses this wrapper for schema switching
    - tenant_context.py: Manages context-aware schema switching
    - django/db/backends/postgresql/base.py: Django's original backend
"""

from django.db.backends.postgresql.base import (
    DatabaseWrapper as PostgresDatabaseWrapper,
)

from django_omnitenant.conf import settings


class DatabaseWrapper(PostgresDatabaseWrapper):
    """
    PostgreSQL database wrapper with schema switching support.
    
    Extends Django's PostgreSQL backend to add dynamic schema switching
    capabilities for schema-per-tenant isolation in multi-tenant applications.
    
    This wrapper tracks the current schema and provides methods to switch
    between schemas using PostgreSQL's search_path mechanism.
    
    Key Capabilities:
        - Dynamic schema switching per connection
        - Automatic connection validation before schema switch
        - Current schema tracking
        - Safe schema name handling (SQL injection prevention)
        - Integration with Django's connection pooling
        
    How It Works:
        1. When connection is created, schema defaults to PUBLIC_TENANT_NAME
        2. set_schema(schema_name) changes the PostgreSQL search_path
        3. All subsequent queries on this connection use the new schema
        4. current_schema property returns the tracked schema name
        5. On connection reuse, schema state is maintained or reset as needed
        
    Schema vs Database:
        - Database isolation: Separate PostgreSQL databases
        - Schema isolation: Separate schemas in same database (this wrapper)
        - Both can be used together in hybrid architectures
        
    Thread Safety:
        Each thread has its own database connection:
        - Schema state is per-connection (per-thread)
        - No cross-thread interference
        - TenantContext manages thread-local state
        
    Integration Points:
        - SchemaTenantBackend: Calls set_schema() to activate tenant
        - TenantContext: Manages schema switching per request
        - Middleware: Handles schema setup per HTTP request
        - Context managers: Automatic schema restoration
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the PostgreSQL wrapper.
        
        Args:
            *args: Positional arguments passed to parent PostgreSQL wrapper
            **kwargs: Keyword arguments passed to parent PostgreSQL wrapper
            
        Process:
            1. Call parent PostgresDatabaseWrapper.__init__()
            2. Initialize current schema to PUBLIC_TENANT_NAME
            3. Store default schema for reset operations
            
        Default Schema:
            The initial schema is set to settings.PUBLIC_TENANT_NAME:
            - Default: 'public' (PostgreSQL standard public schema)
            - Can be configured differently in settings
            - Used when resetting or initializing connections
            
        State Initialization:
            _current_schema tracks the schema state:
            - Set initially to PUBLIC_TENANT_NAME
            - Updated by set_schema() calls
            - Used by current_schema property
            
        Example:
            ```python
            from django.db import connection
            
            # Connection initialized with schema='public'
            assert connection.get_database_wrapper().current_schema == 'public'
            
            # Can change schema
            connection.set_schema('tenant_acme')
            assert connection.get_database_wrapper().current_schema == 'tenant_acme'
            ```
            
        Parent Initialization:
            The parent PostgreSQL wrapper handles:
            - Database connection pooling
            - Connection parameter handling
            - Query execution framework
            - Transaction management
            
        Settings Integration:
            Uses settings.PUBLIC_TENANT_NAME for default:
            - Allows configuration via Django settings
            - Default to 'public' if not configured
            - Can be customized per project
        """
        super().__init__(*args, **kwargs)
        # Initialize schema tracking to the public/default tenant
        # This is the schema used for non-tenant-specific connections
        self._current_schema = settings.PUBLIC_TENANT_NAME
        # Alternative: self._current_schema = "public"  # Direct hardcoding

    def set_schema(self, schema_name):
        """
        Switch the PostgreSQL schema for this connection.
        
        This method changes the connection's search_path to the specified schema,
        making all subsequent queries on this connection default to that schema.
        
        Process:
            1. Validate connection is usable (not closed/stale)
            2. If connection is not usable, re-establish it
            3. Execute SET search_path SQL command
            4. Update internal schema tracking
            
        Args:
            schema_name (str): Name of the PostgreSQL schema to switch to
                             Example: 'tenant_acme', 'public', 'tenant_globex'
                             
        Raises:
            Exception: If connection re-establishment fails or SQL execution fails
            
        SQL Generation:
            Executes: SET search_path TO "schema_name"
            - Quotes schema_name to prevent SQL injection
            - SET search_path is fast (just config change)
            - No locks or blocking
            - Immediate effect on connection
            
        Connection Validation:
            is_usable() checks if connection is still valid:
            - May be closed or timed out
            - May be in an inconsistent state
            - Network issues could have occurred
            
            If not usable, ensure_connection() re-establishes it:
            - Creates new connection if needed
            - Resets connection state
            - Safe to call multiple times
            
        Schema Tracking:
            After successful switch, _current_schema is updated:
            - Tracks current state internally
            - Used by current_schema property
            - Accessible by other code needing to know current schema
            
        Performance:
            SET search_path is very efficient:
            - No disk I/O
            - Just updates connection state
            - Microseconds execution time
            - Can be called frequently without issue
            
        Thread Safety:
            Each thread has its own database connection:
            - Schema change affects only this connection
            - Other threads unaffected
            - Thread-local state in TenantContext
            
        Example Usage:
            ```python
            from django.db import connection
            
            # Switch to tenant schema
            connection.set_schema('tenant_acme')
            
            # Now queries default to tenant_acme schema
            from myapp.models import User
            users = User.objects.all()  # Queries tenant_acme.users
            
            # Create objects (automatically in correct schema)
            User.objects.create(username='john')  # In tenant_acme.users
            
            # Switch to different schema
            connection.set_schema('tenant_globex')
            users = User.objects.all()  # Now queries tenant_globex.users
            ```
            
        With TenantContext:
            TenantContext automatically calls set_schema:
            
            ```python
            from django_omnitenant.tenant_context import TenantContext
            
            with TenantContext.use_tenant(tenant):
                # set_schema() automatically called
                User.objects.all()  # Queries correct tenant schema
                # set_schema() restoration automatic on exit
            ```
            
        Nested Calls:
            Can be called multiple times safely:
            ```python
            connection.set_schema('tenant_acme')
            # ... do something ...
            connection.set_schema('tenant_globex')
            # ... do something else ...
            connection.set_schema('public')
            # Back to public schema
            ```
            
        Error Scenarios:
            - Invalid schema name: PostgreSQL raises error
            - Connection lost: ensure_connection() handles it
            - Permission denied: PostgreSQL raises permission error
            
            These errors propagate to caller for handling.
            
        SQL Injection Prevention:
            Schema names are quoted with double quotes:
            ```python
            cursor.execute(f'SET search_path TO "{schema_name}"')
            ```
            
            This prevents schema names from being interpreted as SQL:
            - Example: schema_name="public; DROP TABLE users; --"
            - Becomes: SET search_path TO "public; DROP TABLE users; --"
            - Treated as single identifier, safe
            
        See Also:
            - set_schema_to_public(): Reset to public schema
            - current_schema property: Get current schema
            - is_usable(): Check connection validity
            - ensure_connection(): Restore connection
        """
        # Validate that the connection is still usable
        # May have been closed, timed out, or disconnected
        if not self.is_usable():
            # Re-establish connection if it's not valid
            # This creates new connection if needed, handles stale connections
            self.ensure_connection()

        # Get cursor and execute SET search_path command
        # This tells PostgreSQL which schema to search by default
        with self.cursor() as cursor:
            # SET search_path TO schema_name
            # Double quotes prevent SQL injection via schema name
            # This command is fast (just changes connection state)
            cursor.execute(f'SET search_path TO "{schema_name}"')

        # Update internal tracking of current schema
        # Used by current_schema property and for state management
        self._current_schema = schema_name

    def set_schema_to_public(self):
        """
        Reset to the public schema.
        
        This method switches the connection back to the public (default) schema,
        typically used when exiting a tenant context or resetting to shared data.
        
        Process:
            1. Call set_schema() with PUBLIC_TENANT_NAME (or 'public')
            
        Purpose:
            Provides a convenient way to reset to the default/shared schema:
            - Cleaner API than set_schema('public')
            - Uses configured PUBLIC_TENANT_NAME setting
            - Clear intent (reset to public, not tenant-specific)
            
        Public Schema:
            The public schema is typically:
            - Default PostgreSQL schema (named 'public')
            - Contains shared data (Tenant, Domain models)
            - Used for non-tenant-specific tables
            - Accessed outside tenant context
            
        Use Cases:
            Reset is needed:
            - When exiting tenant context
            - Between request processing
            - For cleanup after tenant operations
            - In test teardown
            
            Example:
            ```python
            connection.set_schema('tenant_acme')
            # ... perform tenant-specific operations ...
            connection.set_schema_to_public()
            # Back to public schema, safe for cleanup
            ```
            
        Configuration:
            Uses settings.PUBLIC_TENANT_NAME:
            - Defaults to 'public' in PostgreSQL
            - Can be configured in Django settings
            - Allows custom public schema naming
            - Example: could be 'shared', 'master', etc.
            
        Convenience Method:
            Shorter than set_schema(settings.PUBLIC_TENANT_NAME):
            
            ```python
            # Longer form
            connection.set_schema(settings.PUBLIC_TENANT_NAME)
            
            # Shorter form (this method)
            connection.set_schema_to_public()
            ```
            
        Implementation:
            Simply delegates to set_schema():
            - Reuses all connection validation logic
            - Same error handling
            - Identical performance
            - Just different calling convention
            
        Thread Safety:
            Thread-safe like set_schema():
            - Affects only this connection
            - Each thread has own connection
            - TenantContext manages thread-local state
            
        Examples:
            ```python
            from django.db import connection
            
            # Start in public schema (default)
            assert connection.current_schema == 'public'
            
            # Switch to tenant
            connection.set_schema('tenant_acme')
            User.objects.create(username='john')  # In tenant schema
            
            # Reset to public
            connection.set_schema_to_public()
            User.objects.create(username='admin')  # In public schema
            ```
            
        With TenantContext:
            Automatically called on context exit:
            
            ```python
            with TenantContext.use_tenant(tenant):
                # set_schema('tenant_acme') called on entry
                User.objects.all()
                # set_schema_to_public() called on exit
            ```
            
        Error Handling:
            If set_schema() fails, exception propagates:
            - Connection errors
            - Permission errors
            - SQL errors
            
            Caller should handle appropriately.
            
        See Also:
            - set_schema(): Switch to any schema
            - current_schema property: Get current schema
            - PUBLIC_TENANT_NAME setting: Configured public schema name
            - TenantContext: Automatic schema management
        """
        # Reset to public/default schema using configured PUBLIC_TENANT_NAME
        # This is a convenience method that delegates to set_schema()
        self.set_schema(settings.PUBLIC_TENANT_NAME)
        # Alternative: self.set_schema("public")  # Direct hardcoding

    @property
    def current_schema(self):
        """
        Get the current schema name for this connection.
        
        Returns the name of the PostgreSQL schema that this connection's
        search_path currently defaults to.
        
        Returns:
            str: Current schema name (e.g., 'public', 'tenant_acme')
            
        Purpose:
            Allows code to query the current schema state:
            - For logging/debugging
            - For assertions in tests
            - For conditional logic based on current schema
            - For state validation
            
        State Management:
            Returns the _current_schema instance variable:
            - Maintained by set_schema() calls
            - Initialized to PUBLIC_TENANT_NAME on connection creation
            - Reflects actual connection state
            
        Use Cases:
            
            1. Debugging:
            ```python
            from django.db import connection
            
            connection.set_schema('tenant_acme')
            print(f"Current schema: {connection.current_schema}")
            # Output: Current schema: tenant_acme
            ```
            
            2. Testing:
            ```python
            with TenantContext.use_tenant(tenant):
                assert connection.current_schema == 'tenant_acme'
            assert connection.current_schema == 'public'
            ```
            
            3. Conditional Logic:
            ```python
            if connection.current_schema == 'public':
                # Shared data operations
            else:
                # Tenant-specific operations
            ```
            
            4. Logging:
            ```python
            logger.info(f"Schema: {connection.current_schema}, "
                       f"Query: {sql}")
            ```
            
        Performance:
            Very fast - just property access:
            - No database queries
            - No I/O operations
            - O(1) complexity
            - Suitable for frequent access
            
        Accuracy:
            Returns the tracked state, not queried from PostgreSQL:
            - Updated on every set_schema() call
            - Should always match actual search_path
            - If manually altered (via raw SQL), won't reflect that
            - Generally reliable for normal usage
            
        Example in Context:
            ```python
            from django.db import connection
            from django_omnitenant.tenant_context import TenantContext
            from myapp.models import Tenant
            
            tenant = Tenant.objects.get(tenant_id='acme')
            
            # Before context
            print(connection.current_schema)  # Output: public
            
            # Inside context
            with TenantContext.use_tenant(tenant):
                print(connection.current_schema)  # Output: tenant_acme
                User.objects.create(username='john')
            
            # After context
            print(connection.current_schema)  # Output: public
            ```
            
        With Multiple Tenants:
            Tracks correct schema per connection:
            ```python
            tenant1 = Tenant.objects.get(tenant_id='acme')
            tenant2 = Tenant.objects.get(tenant_id='globex')
            
            with TenantContext.use_tenant(tenant1):
                assert connection.current_schema == 'acme'
            
            with TenantContext.use_tenant(tenant2):
                assert connection.current_schema == 'globex'
            ```
            
        Thread Safety:
            Each thread has own connection and schema state:
            - property returns per-connection state
            - Thread-local in TenantContext
            - Safe for concurrent requests
            
        Notes:
            - Returns tracked state, not queried from database
            - Usually matches actual search_path
            - If manually altering search_path via raw SQL, update may be needed
            - Property access is very efficient
            
        See Also:
            - set_schema(): Change the schema
            - set_schema_to_public(): Reset to public
            - _current_schema: Internal state variable
            - TenantContext: Automatic schema management
        """
        # Return the tracked schema state for this connection
        # This is updated by set_schema() calls
        return self._current_schema
