"""
Interactive Django Shell with Tenant Context

Django management command for launching interactive Python shell with multi-tenant support.

Purpose:
    Extends Django's built-in shell command to support optional tenant context activation.
    Allows developers to interact with tenant-specific data within an interactive Python
    shell environment while developing or debugging multi-tenant applications.
    
Key Features:
    - Launches standard Django Python shell
    - Optional --tenant-id to activate specific tenant
    - Without --tenant-id: normal Django shell (no tenant scope)
    - With --tenant-id: shell runs in tenant context (queries scoped to tenant)
    - Full access to Django models, ORM, utilities
    - Same shell experience as Django's standard shell command
    
Use Cases:
    - Debugging tenant-specific data issues
    - Testing queries for specific tenant
    - Interactive data inspection without code
    - Troubleshooting tenant isolation problems
    - Quick model queries during development
    - Testing model methods in tenant context
    
Tenant Context:
    When --tenant-id provided:
    - All model queries automatically scoped to tenant
    - User objects filtered to tenant only
    - Cross-tenant access prevented by context
    - Database/schema routing handled automatically
    - Default context used if not specified
    
Usage:
    ```bash
    # Normal shell (no tenant scope)
    python manage.py shell
    
    # Shell with tenant activated
    python manage.py shell --tenant-id=acme
    
    # Shell for specific tenant
    python manage.py shell --tenant-id=beta
    ```
    
Supported Shell Options (inherited from Django):
    -i: Interactive mode
    -c: Command to execute (alternative to interactive)
    
Command Flow:
    1. Parse --tenant-id argument (optional)
    2. If tenant_id provided:
        a. Get Tenant model
        b. Validate tenant exists
        c. Enter tenant context
        d. Start shell within context
    3. If no tenant_id: start normal Django shell
    4. Exit gracefully

Error Handling:
    - Invalid tenant ID: Error shown, shell not started
    - Connection error: Propagated from tenant backend
    - Python errors: Standard Python exception handling

Related:
    - Django's shell: Parent command
    - TenantContext: Manages tenant isolation
    - createtenant: Create tenant to use with --tenant-id

Examples:
    Debugging tenant data:
    ```bash
    $ python manage.py shell --tenant-id=acme
    Tenant 'acme' activated.
    >>> from myapp.models import MyModel
    >>> MyModel.objects.count()  # Only counts ACME's records
    42
    >>> MyModel.objects.first()
    <MyModel: ACME-specific instance>
    ```
    
    Normal shell (no scope):
    ```bash
    $ python manage.py shell
    >>> from myapp.models import MyModel
    >>> MyModel.objects.count()  # Counts ALL records across tenants
    284
    ```
"""

from django.core.management.commands.shell import Command as ShellCommand

from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_tenant_model


class Command(ShellCommand):
    """
    Django management command for interactive shell with tenant support.
    
    This command extends Django's shell command to optionally activate a specific
    tenant context. When a tenant is activated, all database queries within the
    shell run in that tenant's scope, making it useful for debugging and testing
    tenant-specific functionality.
    
    Inheritance:
        Inherits from django.core.management.commands.shell.Command, which provides
        the standard Django interactive Python shell functionality.
    
    Key Differences from Django's shell:
        1. Adds optional --tenant-id argument
        2. Without --tenant-id: behaves like standard Django shell
        3. With --tenant-id: activates tenant context before shell starts
        4. All queries in tenant context are automatically scoped
        5. Validates tenant exists before activating context
    
    Attributes:
        help (str): Help text shown in management command listing
    
    Usage Examples:
        Normal Django shell (all tenants visible):
        ```bash
        $ python manage.py shell
        >>> User.objects.all()  # All users across all tenants
        ```
        
        Tenant-scoped shell (ACME only):
        ```bash
        $ python manage.py shell --tenant-id=acme
        Tenant 'acme' activated.
        >>> User.objects.all()  # Only ACME users
        ```
        
        Interactive debugging:
        ```bash
        $ python manage.py shell --tenant-id=beta
        Tenant 'beta' activated.
        >>> from myapp.models import Order
        >>> Order.objects.filter(status='pending').count()
        # Shows pending orders for Beta only
        >>> Order.objects.first().customer  # Customer in Beta's context
        <Customer: Beta Customer>
        ```
    
    Notes:
        - Tenant validation prevents errors from invalid tenant IDs
        - Shell exits normally when done, context is cleaned up
        - Multiple shell instances can run simultaneously for different tenants
        - Tenant scope only applies within the 'with' context block
    """
    help = "Runs a Django shell with a specific tenant activated."

    def add_arguments(self, parser):
        """
        Add command-line arguments to the command parser.
        
        This method extends the parent shell command's arguments by adding an optional
        --tenant-id argument for specifying which tenant to activate within the shell.
        All other Django shell arguments are inherited (like -c for command execution).
        
        Arguments:
            parser (argparse.ArgumentParser): Django's argument parser for this command.
        
        Custom Arguments:
            --tenant-id (str): OPTIONAL. The tenant_id of the tenant to activate
                within the shell context. If not provided, shell runs without tenant
                context (can access all tenants' data). If provided, shell runs with
                that tenant's context (queries scoped to tenant only).
        
        Django Arguments Inherited (from shell command):
            -i, --interface: Interface to use (ipython, bpython, standard)
            -c CODE, --command CODE: Execute Python code instead of interactive shell
            --no-startup: Don't execute startup code
            [other shell options]: Depends on Django version
        
        Examples:
            ```python
            # Run shell for ACME tenant
            $ manage.py shell --tenant-id=acme
            
            # Run shell for Beta tenant with iPython
            $ manage.py shell --tenant-id=beta -i ipython
            
            # Execute command in ACME's context
            $ manage.py shell --tenant-id=acme -c "from myapp.models import User; print(User.objects.count())"
            
            # Normal shell (no tenant scope)
            $ manage.py shell
            ```
        
        Notes:
            - Tenant ID is optional (unlike createtenantsuperuser)
            - If tenant ID is invalid, error shown before shell starts
            - Parser is modified in-place; no return value
        """
        super().add_arguments(parser)  # Include all parent shell arguments
        parser.add_argument(
            "--tenant-id",
            type=str,
            help="Tenant ID to activate within the shell context. "
                 "If provided, all queries will be scoped to this tenant. "
                 "If omitted, shell runs without tenant scope (can access all tenants)."
        )

    def handle(self, *args, **options):
        """
        Execute the Django shell with optional tenant context.
        
        This method determines whether a tenant context should be activated and
        then starts the interactive shell. If --tenant-id is provided, validates
        it exists and activates it; otherwise starts normal shell.
        
        Arguments:
            *args: Positional arguments (typically empty)
            **options (dict): Command options including:
                - tenant_id (str, optional): Tenant to activate, if provided
                - interface (str, optional): Shell interface (ipython, bpython, etc)
                - command (str, optional): Python code to execute instead of interactive
                - [other options]: Other Django shell options
        
        Returns:
            None: Django management commands don't return values. Output via stdout/stderr.
        
        Process Flow (with tenant_id):
            ```
            1. Extract tenant_id from options
                tenant_id = options.get('tenant_id')
            
            2. If tenant_id provided:
                if tenant_id:
                    # Proceed with tenant activation
                    
                    a. Get Tenant model
                        Tenant = get_tenant_model()
                    
                    b. Query for tenant
                        tenant = Tenant.objects.get(tenant_id=tenant_id)
                        # Raises Tenant.DoesNotExist if not found
                    
                    c. Output confirmation (if not running -c command)
                        self.stdout.write(
                            self.style.SUCCESS(f'Tenant {tenant_id} activated.')
                        )
                    
                    d. Enter tenant context
                        with TenantContext.use_tenant(tenant):
                            # All queries now scoped to this tenant
                    
                    e. Start shell within context
                        super().handle(*args, **options)
                        # Interactive shell with tenant scope
                    
                    f. Exit context when shell closes
                        # Context automatically cleaned up
            
            3. If no tenant_id:
                else:
                    # Start normal shell without tenant scope
                    super().handle(*args, **options)
            ```
        
        Usage Examples:
            Tenant-scoped shell:
            ```bash
            $ python manage.py shell --tenant-id=acme
            Tenant 'acme' activated.
            Python 3.10.0 (default, Oct  5 2021) ...
            Type "help", "copyright", "credits" or "license" ...
            >>> from myapp.models import User
            >>> User.objects.all()  # ACME users only
            <QuerySet [<User: john@acme.com>, <User: jane@acme.com>]>
            ```
            
            Normal shell:
            ```bash
            $ python manage.py shell
            Python 3.10.0 (default, Oct  5 2021) ...
            Type "help", "copyright", "credits" or "license" ...
            >>> from myapp.models import User
            >>> User.objects.all()  # All users
            <QuerySet [<User: john@acme.com>, <User: jane@beta.com>, ...]>
            ```
            
            Command execution in tenant:
            ```bash
            $ python manage.py shell --tenant-id=acme -c "from myapp.models import User; print(User.objects.count())"
            Tenant 'acme' activated.
            2
            # Note: Tenant message shown, then result (2 = ACME's users)
            ```
        
        Error Handling:
            
            Case 1: Tenant doesn't exist
            ```bash
            $ python manage.py shell --tenant-id=nonexistent
            # Error: Tenant with ID 'nonexistent' does not exist.
            # Shell does not start
            ```
            
            Case 2: No tenant_id (normal operation)
            ```bash
            $ python manage.py shell
            # No activation message, normal Django shell starts
            ```
            
            Case 3: Connection error
            ```bash
            $ python manage.py shell --tenant-id=acme
            # If tenant's database unreachable, error from backend
            ```
        
        Important Characteristics:
            - Non-blocking on invalid tenant (error shown, exit cleanly)
            - Tenant context is scoped to shell session
            - Multiple shell instances can run for different tenants simultaneously
            - Shell exit returns to normal scope (context cleaned automatically)
            - No changes to database connection outside shell scope
        
        Notes:
            - Optional --tenant-id makes this different from required arguments in other commands
            - Shell with tenant is useful for debugging, testing, development
            - Production use requires careful credential handling
            - Tenant context prevents accidental cross-tenant access
            - Output formatting uses Django conventions (SUCCESS/ERROR colors)
        
        Integration Points:
            - Calls get_tenant_model(): Gets configured Tenant model
            - Calls TenantContext.use_tenant(): Activates tenant scope
            - Calls super().handle(): Starts Django's shell command
            - Uses self.stdout and self.stderr: Django's command output streams
            - Uses self.style: Django's output formatting (SUCCESS, ERROR)
        """
        # Extract tenant_id from options (None if not provided)
        tenant_id = options.get("tenant_id")
        
        # Check if user provided a tenant_id to activate
        if tenant_id:
            # Get the Tenant model class (can be customized via settings)
            Tenant = get_tenant_model()
            
            # Validate tenant exists before starting shell
            try:
                tenant = Tenant.objects.get(tenant_id=tenant_id)
            except Tenant.DoesNotExist:
                # Tenant not found - show error and return (don't start shell)
                self.stderr.write(
                    self.style.ERROR(f"Tenant with ID '{tenant_id}' does not exist.")
                )
                return
            
            # Confirm tenant activation to user (good for UX)
            self.stdout.write(
                self.style.SUCCESS(f"Tenant '{tenant_id}' activated.")
            )
            
            # Enter tenant context: all subsequent queries scoped to this tenant
            # Start shell within the context so all shell queries use tenant scope
            with TenantContext.use_tenant(tenant):
                # Call parent's handle to start Django's shell within tenant context
                super().handle(*args, **options)
        else:
            # No tenant_id provided - start normal Django shell (no tenant scope)
            # User can access all tenants' data
            super().handle(*args, **options)
