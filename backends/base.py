"""
Base Tenant Backend Module

This module defines the abstract base class for all tenant backends in django-omnitenant.

Tenant backends are responsible for:
1. Provisioning tenant resources (database, schema, storage, etc.)
2. Tearing down tenant resources when deleted
3. Running tenant-specific database migrations
4. Binding/activating tenant context during request handling
5. Emitting signals at key lifecycle events

Backend Hierarchy:
    BaseTenantBackend (abstract base)
    ├── DatabaseTenantBackend (database-per-tenant isolation)
    ├── SchemaTenantBackend (schema-per-tenant isolation)
    └── [Custom backends]

Architecture:
    The backend pattern allows different isolation strategies to be pluggable.
    Each backend implements the same interface but with different provisioning logic.

Isolation Strategies:
    1. Database-per-Tenant: Each tenant gets a separate database
    2. Schema-per-Tenant: Each tenant gets a schema in shared PostgreSQL database
    3. Custom: Application-specific isolation methods

Lifecycle Events:
    The backend emits Django signals at key points:
    - tenant_created: After tenant resources are provisioned
    - tenant_migrated: After migrations run for tenant
    - tenant_deleted: After tenant resources are torn down
    - tenant_activated: When entering tenant context
    - tenant_deactivated: When exiting tenant context

Usage:
    ```python
    from django_omnitenant.utils import get_tenant_backend
    from django_omnitenant.models import Tenant

    # Get backend for a tenant
    tenant = Tenant.objects.get(tenant_id='acme')
    backend = get_tenant_backend(tenant)

    # Provision the tenant
    backend.create(run_migrations=True)

    # Use the tenant
    with backend.activate():
        # Perform operations in tenant context
        pass

    # Tear down the tenant
    backend.delete()
    ```

Custom Backend Implementation:
    ```python
    from django_omnitenant.backends.base import BaseTenantBackend

    class CustomBackend(BaseTenantBackend):
        def bind(self):
            # Custom binding logic
            pass

        def create(self, run_migrations=False):
            # Custom creation logic
            super().create(run_migrations)

        def delete(self):
            # Custom deletion logic
            super().delete()
    ```

Related:
    - signals.py: Tenant lifecycle signals
    - database_backend.py: Database-per-tenant implementation
    - schema_backend.py: Schema-per-tenant implementation
    - models.py: BaseTenant model
"""

from django_omnitenant.signals import (
    tenant_created,
    tenant_migrated,
    tenant_deleted,
    tenant_activated,
    tenant_deactivated,
)


class BaseTenantBackend:
    """
    Abstract base class for tenant backends.

    This class defines the interface and lifecycle for tenant resource management.
    Subclasses implement specific isolation strategies (database, schema, etc.).

    Responsibilities:
        1. Provisioning tenant resources during creation
        2. Tearing down resources during deletion
        3. Running migrations specific to a tenant
        4. Binding tenant context to Django settings
        5. Activating/deactivating tenant context
        6. Emitting lifecycle signals

    Lifecycle Methods:
        create() -> bind() -> tenant_created signal
        migrate() -> tenant_migrated signal
        delete() -> tenant_deleted signal
        activate() -> tenant_activated signal
        deactivate() -> tenant_deactivated signal

    Abstract Methods (must be implemented by subclasses):
        - bind(): Attach tenant resources to Django settings

    Attributes:
        tenant (BaseTenant): The tenant instance this backend manages

    Design Pattern:
        Uses the Template Method pattern:
        - Base class defines the workflow
        - Subclasses implement specific steps (bind())
        - Signals are emitted at standard points

    Thread Safety:
        Each backend instance is tied to a specific tenant context.
        Use within TenantContext for thread-safe operations.
    """

    def __init__(self, tenant):
        """
        Initialize the backend with a specific tenant.

        Args:
            tenant (BaseTenant): The tenant instance to manage

        Example:
            ```python
            from django_omnitenant.backends.base import BaseTenantBackend
            from myapp.models import Tenant

            tenant = Tenant.objects.get(tenant_id='acme')
            backend = BaseTenantBackend(tenant)
            ```

        Note:
            This is typically called by get_tenant_backend() utility function,
            not directly by application code.
        """
        self.tenant = tenant

    def create(self, run_migrations=False):
        """
        Provision tenant resources (database, schema, storage, etc.).

        This method creates all necessary resources for a new tenant:
        1. Binds resources to Django settings
        2. Emits tenant_created signal for connected handlers
        3. Optionally runs initial migrations

        Args:
            run_migrations (bool, optional): Whether to run migrations after creation.
                                           Default is False. Set to True to run
                                           initial migrations immediately.

        Process:
            1. Call bind() to attach resources to settings
            2. Send tenant_created signal
            3. If run_migrations=True, call migrate()

        Raises:
            Exception: Various exceptions depending on backend implementation
                      (database connection errors, permission issues, etc.)

        Lifecycle:
            This is typically called during:
            - Tenant creation via management command (createtenant)
            - Programmatic tenant provisioning
            - Test setup

        Signals:
            Emits: tenant_created(sender=Tenant, tenant=instance)
            Connected handlers run after resources are created.

        Examples:
            ```python
            from django_omnitenant.utils import get_tenant_backend
            from myapp.models import Tenant

            # Create a new tenant
            tenant = Tenant.objects.create(
                tenant_id='acme',
                name='Acme Corporation'
            )

            # Provision resources
            backend = get_tenant_backend(tenant)
            backend.create(run_migrations=True)
            # Creates database/schema + runs migrations + emits signal

            # Later: Just provision without migrations
            backend.create(run_migrations=False)
            ```

        Error Handling:
            Database errors, permission issues, etc. will raise exceptions.
            Ensure proper error handling when calling in production:

            ```python
            try:
                backend.create(run_migrations=True)
            except Exception as e:
                logger.error(f"Failed to create tenant: {e}")
                tenant.delete()  # Clean up if provisioning failed
            ```

        See Also:
            - delete(): Remove tenant resources
            - migrate(): Run migrations for existing tenant
            - bind(): Low-level resource binding (implemented by subclass)
        """
        # Step 1: Bind the tenant resources to Django settings
        # This makes the tenant's database/schema accessible
        self.bind()

        # Step 2: Emit tenant_created signal for any connected handlers
        # Handlers can perform custom setup for the newly created tenant
        tenant_created.send(sender=self.tenant.__class__, tenant=self.tenant)

        # Step 3: Optionally run migrations if requested
        if run_migrations:
            self.migrate()

    def delete(self):
        """
        Tear down tenant resources (database, schema, storage, etc.).

        This method removes all resources associated with a tenant:
        1. Emits tenant_deleted signal for cleanup handlers
        2. Subclass implementation removes actual resources

        Process:
            1. Send tenant_deleted signal
            2. Backend implementation removes resources

        Raises:
            Exception: Various exceptions depending on backend implementation
                      (database connection errors, permission issues, etc.)

        Lifecycle:
            This is typically called during:
            - Tenant deletion via management command (deleteenant)
            - Programmatic tenant cleanup
            - User-initiated tenant removal
            - Application shutdown/migration

        Signals:
            Emits: tenant_deleted(sender=Tenant, tenant=instance)
            Handlers run BEFORE resource deletion (so they have access to tenant).

        Warning:
            This is destructive! Once deleted, the tenant data cannot be recovered
            unless you have backups. Typically:
            1. Archive tenant data if needed for compliance
            2. Call backend.delete()
            3. Delete Tenant model instance

        Examples:
            ```python
            from django_omnitenant.utils import get_tenant_backend
            from myapp.models import Tenant

            # Get tenant to delete
            tenant = Tenant.objects.get(tenant_id='acme')

            # Archive if needed
            archive_tenant_data(tenant)

            # Tear down resources
            backend = get_tenant_backend(tenant)
            backend.delete()
            # Removes database/schema + emits signal

            # Clean up the model
            tenant.delete()
            ```

        Error Handling:
            Handle errors carefully during deletion:

            ```python
            try:
                backend.delete()
            except Exception as e:
                logger.error(f"Error deleting tenant: {e}")
                # May need manual intervention
                notify_administrators()
            ```

        Idempotency:
            Calling delete() twice should not cause errors.
            Backends should handle already-deleted resources gracefully.

        See Also:
            - create(): Provision tenant resources
            - tenant_deleted signal: For cleanup handlers
        """
        # Emit signal before deletion so handlers can access tenant if needed
        # Handlers can perform cleanup tasks (archive data, notify users, etc.)
        tenant_deleted.send(sender=self.tenant.__class__, tenant=self.tenant)

    def migrate(self, *args, **kwargs):
        """
        Run tenant-specific database migrations.

        This method applies pending migrations to the tenant's database/schema.
        The specific implementation depends on the backend (database vs schema).

        Args:
            *args: Additional positional arguments for migration command
            **kwargs: Additional keyword arguments for migration command
                     Common kwargs:
                     - app_label: Migrate specific app only
                     - migration_name: Migrate to specific migration
                     - verbosity: Output verbosity level

        Process:
            1. Emits tenant_migrated signal
            2. Backend runs Django migrations for the tenant
            3. Signal handlers can perform post-migration setup

        Raises:
            Exception: Migration errors (syntax errors, conflicts, etc.)

        Lifecycle:
            This is typically called during:
            - Initial tenant creation (if create(run_migrations=True))
            - Django version upgrades
            - Application deployments
            - Management command: migratetenant
            - Programmatic tenant updates

        Signals:
            Emits: tenant_migrated(sender=Tenant, tenant=instance)
            Handlers run after migrations are applied.

        Examples:
            ```python
            from django_omnitenant.utils import get_tenant_backend
            from myapp.models import Tenant

            # Run all pending migrations for tenant
            tenant = Tenant.objects.get(tenant_id='acme')
            backend = get_tenant_backend(tenant)
            backend.migrate()

            # Migrate specific app
            backend.migrate(app_label='myapp')

            # Migrate to specific migration
            backend.migrate(migration_name='0005_custom')

            # With verbosity
            backend.migrate(verbosity=2)
            ```

        Management Command:
            Typically invoked via Django management command:

            ```bash
            python manage.py migratetenant acme
            python manage.py migratealltenants
            ```

        Custom Migration Logic:
            Subclasses can override migrate() for custom behavior:

            ```python
            def migrate(self, *args, **kwargs):
                # Custom pre-migration setup
                self.setup_tenant_schema()

                # Call parent to emit signal
                super().migrate(*args, **kwargs)

                # Custom post-migration setup
                self.seed_tenant_data()
            ```

        Error Handling:
            Handle migration errors carefully:

            ```python
            try:
                backend.migrate()
            except Exception as e:
                logger.error(f"Migration failed for {self.tenant}: {e}")
                # Tenant may be in inconsistent state
                notify_administrators()
            ```

        Performance Considerations:
            - Migrations run sequentially per tenant
            - Large migrations may take time
            - Consider running during maintenance windows
            - Monitor database for locks/performance issues

        See Also:
            - create(): Provision and optionally migrate
            - management commands: migratetenant, migratealltenants
            - tenant_migrated signal: For post-migration handlers
        """
        # Emit tenant_migrated signal to notify listeners
        # Handlers can perform post-migration setup tasks
        tenant_migrated.send(sender=self.tenant.__class__, tenant=self.tenant)

    def bind(self):
        """
        Attach tenant resources (DB/schema/etc) to Django settings.

        This abstract method must be implemented by subclasses to attach the tenant's
        resources to Django's configuration. The specific implementation depends on
        the isolation strategy (database, schema, etc.).

        Must Override:
            Subclasses MUST implement this method. Calling on BaseTenantBackend
            will raise NotImplementedError.

        Purpose:
            After bind() is called, Django's connections and routers should be
            configured to use the tenant's resources for subsequent queries.

        Responsibilities:
            1. Update DATABASES setting if using database-per-tenant
            2. Set search_path for schema-per-tenant
            3. Configure any other tenant-specific resources
            4. Ensure the tenant context is activated

        Lifecycle:
            Called during:
            - create(): When provisioning new tenant
            - Within TenantContext when activating a tenant
            - Request middleware when setting up tenant

        Examples:

            Database-per-tenant implementation:
            ```python
            class DatabaseTenantBackend(BaseTenantBackend):
                def bind(self):
                    # Create/register database connection for tenant
                    DATABASES[self.tenant.db_alias] = {
                        'ENGINE': 'django.db.backends.postgresql',
                        'NAME': self.tenant.database_name,
                        'HOST': 'db.example.com',
                    }
                    # Reset connection to use new config
                    reset_db_connection(self.tenant.db_alias)
            ```

            Schema-per-tenant implementation:
            ```python
            class SchemaTenantBackend(BaseTenantBackend):
                def bind(self):
                    # Set PostgreSQL search_path to tenant schema
                    with connections['default'].cursor() as cursor:
                        cursor.execute(
                            f"SET search_path TO {self.tenant.schema_name}"
                        )
            ```

            Custom implementation:
            ```python
            class CustomBackend(BaseTenantBackend):
                def bind(self):
                    # Your custom resource binding logic
                    configure_tenant_storage(self.tenant)
                    configure_tenant_cache(self.tenant)
                    configure_tenant_services(self.tenant)
            ```

        Error Handling:
            Errors during bind() should be handled carefully:

            ```python
            try:
                backend.bind()
            except Exception as e:
                logger.error(f"Failed to bind tenant {self.tenant}: {e}")
                raise
            ```

        Thread Safety:
            bind() should be called within a TenantContext to ensure
            thread-local state is properly managed.

        See Also:
            - create(): Calls bind() and emits signal
            - TenantContext: Context manager for tenant switching
            - database_backend.py: Example database-per-tenant bind()
            - schema_backend.py: Example schema-per-tenant bind()
        """
        raise NotImplementedError

    def activate(self):
        """
        Signal that tenant context is being activated.

        This method emits the tenant_activated signal to notify handlers that
        a tenant context is being entered. This is typically called at the start
        of a request or when explicitly switching tenant context.

        Signals:
            Emits: tenant_activated(sender=Tenant, tenant=instance)
            Handlers can perform per-request/context setup

        Lifecycle:
            Called when:
            - Request middleware activates tenant for request
            - Explicitly entering TenantContext
            - Task starts for specific tenant (Celery, etc.)
            - Any operation switching to tenant context

        Usage:
            ```python
            from django_omnitenant.tenant_context import TenantContext

            # Context manager handles activate/deactivate automatically
            with TenantContext.use_tenant(tenant):
                # tenant.activate() is called here
                # Perform operations
                # tenant.deactivate() is called here
            ```

            Manual usage:
            ```python
            backend = get_tenant_backend(tenant)
            backend.activate()
            try:
                # Perform operations in tenant context
                process_tenant_data()
            finally:
                backend.deactivate()
            ```

        Signal Handlers:
            Typical handlers for tenant_activated:

            ```python
            @receiver(tenant_activated)
            def setup_tenant_logging(sender, tenant, **kwargs):
                # Set up logging context
                structlog.contextvars.bind_contextvars(
                    tenant_id=tenant.tenant_id
                )

            @receiver(tenant_activated)
            def load_tenant_config(sender, tenant, **kwargs):
                # Load tenant-specific configuration
                cache.set(f'config_{tenant.id}', load_config(tenant))
            ```

        Performance:
            activate() is called frequently (every request). Handlers should
            be fast to minimize impact on request latency.

        Use Cases:
            1. Initializing tenant-specific logging context
            2. Loading tenant configuration
            3. Setting up tenant-specific caches
            4. Initializing telemetry/metrics
            5. Configuring feature flags per tenant

        Related:
            - deactivate(): Called when exiting tenant context
            - TenantContext: Context manager for tenant activation
            - tenant_activated signal: For implementing activation handlers

        Note:
            Does not switch actual database/schema (bind() does that).
            Only emits signal for handlers to perform setup.
        """
        # Emit tenant_activated signal for connected handlers
        tenant_activated.send(sender=self.tenant.__class__, tenant=self.tenant)

    def deactivate(self):
        """
        Signal that tenant context is being deactivated.

        This method emits the tenant_deactivated signal to notify handlers that
        a tenant context is being exited. This is typically called at the end
        of a request or when switching away from a tenant context.

        Signals:
            Emits: tenant_deactivated(sender=Tenant, tenant=instance)
            Handlers can perform cleanup and context reset

        Lifecycle:
            Called when:
            - Request middleware finishes after request processing
            - Explicitly exiting TenantContext
            - Task completes for specific tenant (Celery, etc.)
            - Any operation leaving tenant context

        Usage:
            ```python
            from django_omnitenant.tenant_context import TenantContext

            # Context manager handles activate/deactivate automatically
            with TenantContext.use_tenant(tenant):
                # tenant.activate() is called here
                # Perform operations
                # tenant.deactivate() is called here automatically
            ```

            Manual usage:
            ```python
            backend = get_tenant_backend(tenant)
            backend.activate()
            try:
                # Perform operations in tenant context
                process_tenant_data()
            finally:
                backend.deactivate()  # Called even if error occurs
            ```

        Signal Handlers:
            Typical handlers for tenant_deactivated:

            ```python
            @receiver(tenant_deactivated)
            def cleanup_tenant_logging(sender, tenant, **kwargs):
                # Clear logging context
                structlog.contextvars.clear_contextvars()

            @receiver(tenant_deactivated)
            def flush_tenant_cache(sender, tenant, **kwargs):
                # Clear tenant-specific cache entries
                cache.delete(f'config_{tenant.id}')

            @receiver(tenant_deactivated)
            def record_metrics(sender, tenant, **kwargs):
                # Record timing/metrics for tenant operations
                record_request_time(tenant)
            ```

        Guarantee:
            deactivate() is guaranteed to be called even if errors occur
            during context (similar to try/finally semantics).

        Performance:
            Deactivation is called frequently (every request). Handlers should
            be fast to minimize impact on request completion time.

        Use Cases:
            1. Clearing tenant-specific logging context
            2. Flushing tenant caches
            3. Closing tenant-specific connections
            4. Recording metrics/telemetry
            5. Cleanup of temporary tenant resources

        Exception Safety:
            Exceptions in deactivate() handlers are logged but do not prevent
            context cleanup. Context cleanup continues even if handlers fail.

        Related:
            - activate(): Called when entering tenant context
            - TenantContext: Context manager for tenant deactivation
            - tenant_deactivated signal: For implementing deactivation handlers

        Note:
            Does not switch actual database/schema. Only emits signal for
            handlers to perform cleanup. TenantContext handles actual switching.
        """
        # Emit tenant_deactivated signal for connected handlers
        tenant_deactivated.send(sender=self.tenant.__class__, tenant=self.tenant)
