"""
Django Signals for Multi-Tenancy Events

This module defines Django signals that are emitted at key points in the tenant lifecycle.
These signals allow applications to hook into tenant creation, deletion, migration, and
activation events without modifying the core django-omnitenant code.

Signals provide a decoupled way to respond to tenant events. Applications can register
signal handlers to perform custom logic such as:
    - Setting up tenant-specific resources (S3 buckets, API keys, etc.)
    - Sending notifications when tenants are created or deleted
    - Performing cleanup operations when tenants are destroyed
    - Logging tenant lifecycle events
    - Syncing tenant data with external systems
    - Running tenant-specific initialization logic

Signal Documentation:
    - tenant_created: Emitted after a tenant and its schema/database are created
    - tenant_deleted: Emitted after a tenant and its schema/database are destroyed
    - tenant_migrated: Emitted after database migrations are run for a tenant
    - tenant_activated: Emitted when entering a tenant context
    - tenant_deactivated: Emitted when exiting a tenant context

Usage:
    ```python
    from django.dispatch import receiver
    from django_omnitenant.signals import tenant_created, tenant_deleted
    from django_omnitenant.models import Tenant
    
    @receiver(tenant_created, sender=Tenant)
    def setup_tenant_resources(sender, tenant, **kwargs):
        # Perform setup operations for new tenant
        create_s3_bucket_for_tenant(tenant)
        initialize_tenant_features(tenant)
        
    @receiver(tenant_deleted, sender=Tenant)
    def cleanup_tenant_resources(sender, tenant, **kwargs):
        # Perform cleanup operations for deleted tenant
        delete_s3_bucket_for_tenant(tenant)
        notify_administrators(f"Tenant {tenant.name} deleted")
    ```

Related:
    - Django Signals: https://docs.djangoproject.com/en/stable/topics/signals/
    - TenantContext: For managing tenant activation/deactivation
    - Management Commands: Use these signals during tenant operations
"""

from django.dispatch import Signal


# Tenant Lifecycle Signals
# ========================

tenant_created = Signal()
"""
Signal emitted after a tenant is successfully created.

This signal is sent after:
    1. The Tenant model instance is created and saved to the database
    2. The tenant's database schema/database is provisioned
    3. Initial migrations are applied to the tenant's database
    
Sender: The Tenant model class
Providing Arguments:
    - tenant (BaseTenant): The newly created tenant instance
    - created (bool): Always True for this signal
    
Timing: Sent AFTER all setup is complete (schema created, migrations run)

Use Cases:
    - Initialize tenant-specific resources (storage buckets, API keys, etc.)
    - Send welcome emails to tenant admins
    - Set up tenant billing accounts
    - Create default tenant configuration
    - Log tenant creation events
    - Sync tenant with external systems

Example Signal Handler:
    ```python
    from django.dispatch import receiver
    from django_omnitenant.signals import tenant_created
    from myapp.models import TenantBillingAccount
    
    @receiver(tenant_created)
    def setup_billing_for_new_tenant(sender, tenant, **kwargs):
        # Create billing account for the tenant
        TenantBillingAccount.objects.create(
            tenant=tenant,
            plan='free',
            status='active'
        )
        # Send notification
        notify_team(f"New tenant created: {tenant.name}")
    ```

Warning:
    If a signal handler raises an exception, the tenant creation may be rolled back
    depending on the transaction context. Handle exceptions appropriately.
"""


tenant_deleted = Signal()
"""
Signal emitted after a tenant is successfully deleted.

This signal is sent after:
    1. All tenant data is removed from the database
    2. The tenant's database schema/database is torn down
    3. The Tenant model instance is deleted from the master database
    
Sender: The Tenant model class
Providing Arguments:
    - tenant (BaseTenant): The deleted tenant instance (dict-like with former data)
    - deleted (bool): Always True for this signal
    
Timing: Sent AFTER all cleanup is complete (schema dropped, data removed)

Use Cases:
    - Clean up tenant-specific resources (storage buckets, API keys, etc.)
    - Send notification that tenant has been deleted
    - Archive tenant data if required by compliance
    - Update billing records (cancel subscription, refund, etc.)
    - Remove tenant from external systems
    - Clean up background jobs tied to tenant
    - Log tenant deletion events

Example Signal Handler:
    ```python
    from django.dispatch import receiver
    from django_omnitenant.signals import tenant_deleted
    from myapp.tasks import cleanup_external_services
    
    @receiver(tenant_deleted)
    def cleanup_tenant_resources(sender, tenant, **kwargs):
        # Clean up storage
        delete_s3_bucket(tenant.aws_bucket_key)
        
        # Update billing system
        cancel_subscription(tenant.stripe_customer_id)
        
        # Remove from external services
        cleanup_external_services.delay(tenant.id)
        
        # Send notification
        notify_compliance_team(f"Tenant {tenant.name} deleted at {timezone.now()}")
    ```

Warning:
    At the time this signal is sent, the tenant data no longer exists in the database.
    Use the tenant argument (passed as dict-like object) to access former tenant data,
    but be aware that related objects may already be deleted.
"""


tenant_migrated = Signal()
"""
Signal emitted after database migrations are successfully applied to a tenant.

This signal is sent after:
    1. Django's migrate command completes for a specific tenant
    2. All pending migrations are applied to the tenant's database/schema
    3. The migration process returns successfully
    
Sender: The Tenant model class
Providing Arguments:
    - tenant (BaseTenant): The tenant for which migrations were run
    - migrated (bool): Always True for this signal
    
Timing: Sent AFTER all migrations are applied

Use Cases:
    - Run tenant-specific data transformations
    - Seed tenant-specific initial data
    - Update tenant version/feature flags
    - Verify tenant database integrity after migration
    - Trigger tenant-specific post-migration hooks
    - Log migration completion
    - Update tenant status to reflect new schema version

Example Signal Handler:
    ```python
    from django.dispatch import receiver
    from django_omnitenant.signals import tenant_migrated
    from myapp.models import TenantFeatureFlags
    
    @receiver(tenant_migrated)
    def activate_new_features(sender, tenant, **kwargs):
        # Enable new features after migration
        flags = TenantFeatureFlags.objects.get_or_create(tenant=tenant)[0]
        
        # Check if migration includes new_feature_xyz
        from django.core.management import call_command
        flags.has_new_reporting = True
        flags.save()
        
        # Seed initial data if new tables were created
        seed_tenant_initial_data(tenant)
        
        # Log the migration
        logger.info(f"Tenant {tenant.name} migrations completed successfully")
    ```

Note:
    This signal is typically used in management commands or celery tasks that run
    migrations for individual tenants (e.g., migratetenant management command).
"""


# Tenant Context Signals
# ======================

tenant_activated = Signal()
"""
Signal emitted when entering a tenant context.

This signal is sent when:
    1. TenantContext.use_tenant() context manager is entered
    2. A specific tenant becomes the "current tenant" for the request/context
    3. Middleware activates a tenant for a request
    4. An explicit context switch occurs via TenantContext
    
Sender: The Tenant model class
Providing Arguments:
    - tenant (BaseTenant): The tenant being activated
    - activated (bool): Always True for this signal
    
Timing: Sent BEFORE the context body is executed (immediately when entering context)

Use Cases:
    - Initialize tenant-specific caches
    - Set up logging context with tenant info
    - Configure tenant-specific feature flags
    - Load tenant-specific settings
    - Initialize tenant-specific metrics/telemetry
    - Set up audit logging context
    - Verify tenant is accessible/active

Example Signal Handler:
    ```python
    from django.dispatch import receiver
    from django_omnitenant.signals import tenant_activated
    import logging
    
    logger = logging.getLogger(__name__)
    
    @receiver(tenant_activated)
    def setup_tenant_logging(sender, tenant, **kwargs):
        # Add tenant info to logging context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            tenant_id=tenant.tenant_id,
            tenant_name=tenant.name
        )
        
        # Load tenant-specific settings
        cache.set(f'tenant_config_{tenant.id}', get_tenant_config(tenant))
        
        # Log activation
        logger.info(f"Tenant {tenant.name} activated")
    ```

Performance Note:
    This signal is emitted frequently (once per request, plus any explicit context switches).
    Keep handlers fast to avoid impacting request latency.
"""


tenant_deactivated = Signal()
"""
Signal emitted when exiting a tenant context.

This signal is sent when:
    1. TenantContext.use_tenant() context manager is exited
    2. The current tenant context is cleared
    3. Middleware finalizes tenant context after request
    4. An explicit context switch occurs via TenantContext
    
Sender: The Tenant model class
Providing Arguments:
    - tenant (BaseTenant): The tenant being deactivated
    - deactivated (bool): Always True for this signal
    
Timing: Sent AFTER the context body is executed (when exiting context)

Use Cases:
    - Clean up tenant-specific caches
    - Flush tenant-specific logging context
    - Finalize audit logs for the tenant context
    - Release tenant-specific resources
    - Reset tenant-specific configuration
    - Update tenant-specific metrics/counters
    - Perform context cleanup

Example Signal Handler:
    ```python
    from django.dispatch import receiver
    from django_omnitenant.signals import tenant_deactivated
    
    @receiver(tenant_deactivated)
    def cleanup_tenant_context(sender, tenant, **kwargs):
        # Clear tenant-specific cache
        cache.delete_many([
            f'tenant_config_{tenant.id}',
            f'tenant_user_cache_{tenant.id}'
        ])
        
        # Clear logging context
        structlog.contextvars.clear_contextvars()
        
        # Update metrics
        record_tenant_context_end_time(tenant)
    ```

Performance Note:
    This signal is emitted frequently (once per request, plus any explicit context switches).
    Keep handlers fast and simple to avoid impacting request latency.
    
Exception Handling:
    If a handler raises an exception, it won't prevent context cleanup, but will be
    logged. Ensure handlers are robust and handle errors gracefully.
"""

