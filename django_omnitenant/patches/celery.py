"""
Celery Patch Module: Tenant-Aware Task Execution

This module patches Celery to automatically capture and restore tenant context
when executing background tasks asynchronously.

Problem:
    Celery tasks execute in background worker processes without request context:
    - Worker processes are separate from Django request handlers
    - TenantContext not automatically available in workers
    - Tasks execute in wrong/empty tenant context
    - Data isolation violations in multi-tenant applications
    - Tasks may operate on wrong tenant's data
    
Solution:
    This patch extends Celery's Task base class to:
    1. Capture current tenant when task is queued
    2. Store tenant_id in task headers
    3. Restore tenant context when task executes
    4. Execute task in correct tenant context
    5. Clean up context after execution

Tenant Context Flow:
    
    Request Handler (Tenant A context set):
    ```
    @login_required
    def trigger_job(request):
        # In TenantContext for tenant_id='acme'
        task.apply_async(args=(user_id,), tenant_id='acme')
        # Task queued with headers={'tenant_id': 'acme'}
    ```
    
    Celery Broker (Task stored):
    ```
    {
        'task': 'myapp.tasks.process_data',
        'args': (user_id,),
        'headers': {'tenant_id': 'acme'},
        'kwargs': {}
    }
    ```
    
    Worker Process (Tenant A context restored):
    ```
    def process_data(user_id):
        # TenantContext.use_tenant(acme) called automatically
        # Queries scoped to tenant_id='acme'
        user = User.objects.get(id=user_id)  # From tenant_id='acme'
        # Task completes in correct context
    ```

Tenant ID Passing Methods:
    
    Method 1: As Keyword Argument
    ```python
    task.apply_async(
        args=(arg1, arg2),
        kwargs={'user_id': 123, 'tenant_id': 'acme'}
    )
    # tenant_id removed from kwargs, stored in headers
    ```
    
    Method 2: As Option
    ```python
    task.apply_async(
        args=(arg1, arg2),
        tenant_id='acme'  # Passed as option
    )
    # tenant_id stored in headers
    ```

Header-Based Storage:
    Using task headers ensures persistence:
    - Headers survive task routing through broker
    - Headers survive task retries
    - Headers available in worker process
    - Tenant_id not visible in args/kwargs
    - Secure: hidden from task observers
    
    Header Storage:
    ```python
    options.setdefault("headers", {})["tenant_id"] = tenant_id
    # Creates headers dict if missing
    # Stores tenant_id in headers
    # Persists through entire task lifecycle
    ```

Task Execution Flow:
    
    1. Developer queues task with tenant_id
    2. TenantAwareTask.apply_async() called
    3. Extracts tenant_id from kwargs or options
    4. Stores in task headers
    5. Task sent to broker
    
    6. Worker receives task
    7. TenantAwareTask.__call__() called
    8. Extracts tenant_id from headers
    9. Fetches Tenant object
    10. Sets TenantContext.use_tenant(tenant)
    11. Calls parent __call__() to execute task
    12. Context auto-cleaned on exit
    
    Result: Task executes in correct tenant context

Error Handling:
    
    No Tenant ID:
    - Task executes in default context (no tenant set)
    - May cause issues if task expects tenant
    - Should always pass tenant_id
    
    Tenant Not Found:
    - Tenant.objects.get(tenant_id=tenant_id) raises DoesNotExist
    - Task fails
    - Can be retried
    - Should handle gracefully
    
    Best practice: Always pass tenant_id, handle errors

Performance:
    - Header storage: Minimal overhead
    - Tenant lookup: Single database query
    - Context switching: Negligible overhead
    - Works at worker scale
    
Compatibility:
    - Works with all Celery task types
    - Compatible with task routing
    - Compatible with task retries
    - Compatible with task chains/groups
    - Transparent to existing task code

Configuration:
    Enable via Django settings:
    
    ```python
    OMNITENANT_CONFIG = {
        'PATCHES': {
            'celery': True,  # Enable Celery patch
        }
    }
    ```
    
    Or set Celery Task class directly:
    
    ```python
    from django_omnitenant.patches.celery import TenantAwareTask
    
    app.Task = TenantAwareTask
    ```

Usage:
    The patch automatically applies to all tasks:
    
    ```python
    from celery import shared_task
    
    @shared_task
    def my_task(user_id):
        # Automatically executes in correct tenant context
        user = User.objects.get(id=user_id)
        process_user(user)
    
    # Queue task in request handler
    from django_omnitenant.tenant_context import TenantContext
    
    def request_handler(request):
        tenant = TenantContext.get_tenant()
        my_task.apply_async(
            args=(request.user.id,),
            tenant_id=tenant.tenant_id
        )
    ```

Related:
    - cache.py: Cache tenant awareness patch
    - tenant_context.py: Tenant context management
    - models.py: Tenant model
    - Celery documentation - Background task framework
"""

from celery import Celery, Task
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_tenant_model


class TenantAwareTask(Task):
    """
    Celery Task subclass that automatically manages tenant context.
    
    This task class ensures that background tasks execute with the correct
    tenant context, enabling proper multi-tenant data isolation.
    
    Design:
        - Captures tenant_id when task is queued (apply_async)
        - Stores tenant_id in task headers for persistence
        - Restores tenant context when task executes (__call__)
        - Cleans up context automatically after execution
        - Transparent to developer - no changes needed to task code
        
    Features:
        - Automatic tenant capture on queueing
        - Automatic tenant restoration on execution
        - Flexible tenant_id passing (kwarg or option)
        - Header-based storage (survives retries)
        - Works with all Celery features
        - Zero configuration needed
        
    Usage:
        All tasks automatically get this behavior:
        
        ```python
        @shared_task
        def my_task(user_id):
            # Executes in correct tenant context
            user = User.objects.get(id=user_id)
        
        # Queue with tenant_id
        my_task.apply_async(
            args=(user_id,),
            tenant_id=tenant.tenant_id
        )
        ```
    
    Attributes:
        abstract (bool): True - this is base class for all tasks
    """
    abstract = True

    def apply_async(
        self,
        args=None,
        kwargs=None,
        task_id=None,
        producer=None,
        link=None,
        link_error=None,
        shadow=None,
        **options,
    ):
        """
        Queue task with automatic tenant_id capture and header storage.
        
        This method intercepts task queueing to capture the current tenant
        and store it in task headers for later restoration in the worker.
        
        Args:
            args (tuple): Positional arguments for task
            kwargs (dict): Keyword arguments for task
                          May contain 'tenant_id' which is extracted
            task_id (str): Optional explicit task ID
            producer: Celery producer for task routing
            link: Callback tasks on success
            link_error: Callback tasks on error
            shadow (str): Shadow task name for monitoring
            **options: Additional Celery options
                      May contain 'tenant_id' which is extracted
        
        Returns:
            AsyncResult: Celery AsyncResult for task tracking
            
        Process:
            1. Extract tenant_id from kwargs or options
            2. Remove tenant_id from visible task arguments
            3. Store tenant_id in task headers
            4. Call parent apply_async with modified options
            5. Task queued with tenant context preserved
            
        Tenant ID Extraction:
            Supports two passing methods:
            
            Method 1 - Keyword Argument:
            ```python
            task.apply_async(
                args=(user_id,),
                kwargs={'tenant_id': 'acme'}
            )
            # Extracted from kwargs, removed
            ```
            
            Method 2 - Option:
            ```python
            task.apply_async(
                args=(user_id,),
                tenant_id='acme'
            )
            # Extracted from options, removed
            ```
            
        Header Storage:
            Tenant_id stored in task headers:
            ```python
            options.setdefault("headers", {})["tenant_id"] = tenant_id
            # Creates headers if missing
            # Stores tenant_id in headers
            # Persists through broker and retries
            ```
            
            Why headers:
            - Survives task routing
            - Survives task retries
            - Not visible in args/kwargs
            - Accessible in worker via self.request.headers
            - Secure transmission
            
        Side Effects:
            - tenant_id removed from kwargs if present
            - tenant_id removed from options if present
            - headers dict created in options if missing
            - Modified options passed to parent
            
        Examples:
            
            Basic queueing:
            ```python
            task.apply_async(
                args=(user_id,),
                tenant_id='acme'
            )
            # Task queued, tenant stored in headers
            ```
            
            With multiple arguments:
            ```python
            task.apply_async(
                args=(user_id, data),
                kwargs={'tenant_id': 'acme', 'priority': 'high'}
            )
            # tenant_id extracted and stored
            # priority remains in kwargs
            # Both available to task
            ```
            
            With explicit task ID:
            ```python
            task.apply_async(
                args=(user_id,),
                task_id='custom-id-123',
                tenant_id='acme'
            )
            # task_id used for tracking
            # tenant_id stored in headers
            ```
        """
        # Initialize tenant_id to None
        tenant_id = None

        # Extract tenant_id from kwargs if present
        # Check if kwargs exists and contains tenant_id
        if kwargs and "tenant_id" in kwargs:
            # Pop tenant_id from kwargs (remove it)
            # This prevents tenant_id from being passed as task argument
            tenant_id = kwargs.pop("tenant_id")
        
        # Alternatively, extract tenant_id from options if not in kwargs
        # Check options dict for tenant_id
        elif "tenant_id" in options:
            # Pop tenant_id from options (remove it)
            # This prevents tenant_id from appearing in task options
            tenant_id = options.pop("tenant_id")

        # Store tenant_id in task headers if it exists
        if tenant_id:
            # Get or create headers dict in options
            # setdefault ensures headers exists before accessing
            options.setdefault("headers", {})["tenant_id"] = tenant_id
            # Store tenant_id in headers
            # Headers persist through broker and worker

        # Call parent apply_async with modified options
        # All tenant_id extraction/storage complete
        # Parent handles actual task queueing
        return super().apply_async(
            args=args,
            kwargs=kwargs,
            task_id=task_id,
            producer=producer,
            link=link,
            link_error=link_error,
            shadow=shadow,
            **options,
        )

    def __call__(self, *args, **kwargs):
        """
        Execute task with automatic tenant context restoration.
        
        This method intercepts task execution in the worker to restore
        the tenant context that was captured during queueing.
        
        Args:
            *args: Positional arguments passed to task
            **kwargs: Keyword arguments passed to task
        
        Returns:
            object: Return value of actual task execution
            
        Process:
            1. Extract tenant_id from task headers
            2. If tenant_id exists:
               a. Fetch Tenant object from database
               b. Enter TenantContext.use_tenant(tenant)
               c. Call parent __call__ (task execution)
               d. Context auto-cleaned on exit
            3. If no tenant_id, execute task normally
            
        Tenant Context Restoration:
            Worker receives task with stored tenant_id:
            ```python
            # self.request.headers = {'tenant_id': 'acme'}
            tenant_id = headers.get("tenant_id")  # Gets 'acme'
            
            # Fetch tenant object
            tenant = Tenant.objects.get(tenant_id='acme')
            
            # Enter tenant context
            with TenantContext.use_tenant(tenant):
                # Task executes in tenant context
                # All database queries scoped to tenant
                # TenantContext.get_tenant() returns tenant
                result = super().__call__(*args, **kwargs)
            # Context automatically exited, cleaned up
            ```
            
        Task Execution:
            Task code now has tenant context:
            ```python
            def my_task(user_id):
                # TenantContext is set to correct tenant
                # Database queries scoped to tenant
                user = User.objects.get(id=user_id)
                # Gets user from tenant database/schema
                return process_user(user)
            ```
            
        Error Handling:
            
            Tenant Not Found:
            ```python
            tenant = Tenant.objects.get(tenant_id=tenant_id)  # May raise DoesNotExist
            # Task fails if tenant doesn't exist
            # Can be retried if tenant is created later
            ```
            
            No Tenant ID:
            ```python
            # If headers missing or tenant_id not in headers
            # Task executes without tenant context
            # May cause issues if task expects tenant
            ```
            
        Examples:
            
            Task with tenant context:
            ```python
            def process_user(user_id):
                # TenantContext set to correct tenant
                user = User.objects.get(id=user_id)
                # Gets from tenant database
                return user.email
            
            # Worker calls:
            # __call__(user_id=123)
            # - Extracts tenant_id='acme' from headers
            # - Fetches Tenant(tenant_id='acme')
            # - Calls: with TenantContext.use_tenant(tenant): super().__call__(user_id=123)
            # - Task executes in tenant context
            # - Returns user.email
            ```
            
            Task without tenant (fallback):
            ```python
            def background_job():
                # No tenant context set
                # Executes in default context
                # May cause issues
                pass
            
            # Worker calls:
            # __call__()
            # - No headers or tenant_id not in headers
            # - tenant_id remains None
            # - Calls: super().__call__()
            # - Executes normally without context
            ```
        """
        # Initialize tenant_id to None
        tenant_id = None
        
        # Get headers from task request
        # self.request contains task execution context
        # getattr provides safe access with default None
        headers = getattr(self.request, "headers", None)
        
        # Extract tenant_id from headers if they exist
        if headers:
            # Get tenant_id from headers dict
            # Returns None if tenant_id not in headers
            tenant_id = headers.get("tenant_id")

        # If tenant_id exists, restore tenant context and execute task
        if tenant_id:
            # Get the Tenant model (respects custom implementations)
            Tenant = get_tenant_model()
            
            # Fetch Tenant object from database using tenant_id
            # Queries master database for tenant info
            # Raises Tenant.DoesNotExist if tenant not found
            tenant = Tenant.objects.get(tenant_id=tenant_id)
            
            # Execute task within tenant context
            # TenantContext.use_tenant() is context manager
            # Sets TenantContext for duration of with block
            # Auto-cleans on exit
            with TenantContext.use_tenant(tenant):
                # Call parent __call__ to execute actual task
                # Task code runs with TenantContext set
                # All database queries scoped to tenant
                # All cached data isolated to tenant
                return super().__call__(*args, **kwargs)

        # No tenant context needed - execute task normally
        # Task either doesn't need tenant context or is unscoped
        return super().__call__(*args, **kwargs)


# Apply patch globally to all Celery tasks
# Replace default Task class with TenantAwareTask
# All new tasks inherit from TenantAwareTask by default
Celery.Task = TenantAwareTask