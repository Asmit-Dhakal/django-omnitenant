"""
Show Migration State for All Tenants

Django management command for displaying migration status across all tenants.

Purpose:
    Provides visibility into migration state for each tenant in a multi-tenant
    deployment. Useful for verifying migrations have been applied consistently
    across tenants and identifying tenants with pending or missing migrations.

Key Features:
    - Shows migration state for every tenant
    - Optionally filter by specific app
    - Lists applied and unapplied migrations per tenant
    - Proper error handling per tenant
    - Detailed per-tenant output for troubleshooting
    - Uses tenant-specific backend for each tenant
    - Color-coded output for each tenant for better visibility

Use Cases:
    - Verify migrations: Check if all tenants have same migration state
    - Deployment validation: Confirm migrations applied to all tenants
    - Troubleshooting: Identify tenants with missing migrations
    - Audit: Track which tenants are on which migration versions

Tenant Isolation Context:
    Migration state checked within isolated context:
    - Database-per-tenant: Queries each tenant's database
    - Schema-per-tenant: Queries each tenant's schema
    - Row-level isolation: Queries shared database with tenant filter
    - Each tenant's migration state independently tracked

Usage:
    ```bash
    # Show migrations for all tenants
    python manage.py showmigrationsalltenants

    # Show migrations for specific app across all tenants
    python manage.py showmigrationsalltenants hrms

    # Show with plan format
    python manage.py showmigrationsalltenants --plan

    # Show verbose output
    python manage.py showmigrationsalltenants --verbosity=2
    ```

Command Flow:
    1. Parse app_label argument (if provided)
    2. Get Tenant model from settings
    3. Query database for all tenant instances
    4. For each tenant:
        a. Activate tenant context
        b. Call Django's showmigrations command
        c. Display migration state with color coding
    5. Continue to next tenant even if one fails
    6. Provide summary

Error Handling:
    - Individual tenant failures caught and reported
    - Command continues to show migrations for other tenants
    - Failed tenants listed in output
    - Exception details shown for each failure

Related:
    - migratealltenants: Migrate all tenants
    - migratetenant: Migrate specific tenant
    - showmigrations: Django's standard command (single tenant)

Notes:
    - Does not take tenant_id argument (all tenants)
    - Supports standard Django showmigrations options
    - Helps identify migration inconsistencies across tenants
    - Color-coded for better visual separation
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.core.management.color import Style
from io import StringIO
import sys

from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_backend, get_tenant_model


class ColoredOutput:
    """
    Wrapper for stdout that applies color to all output.

    This class intercepts write() calls and applies a color prefix
    to make tenant outputs visually distinct.
    """

    def __init__(self, original_stdout, color_func):
        self.original_stdout = original_stdout
        self.color_func = color_func

    def write(self, text):
        if text and text.strip():  # Only colorize non-empty lines
            # Apply color to each line
            lines = text.split("\n")
            colored_lines = [self.color_func(line) if line.strip() else line for line in lines]
            self.original_stdout.write("\n".join(colored_lines))
        else:
            self.original_stdout.write(text)

    def flush(self):
        self.original_stdout.flush()

    def isatty(self):
        return self.original_stdout.isatty()


class Command(BaseCommand):
    """
    Management command for showing migrations state on all tenants.

    This command provides a convenient way to view migration status across an entire
    multi-tenant deployment without needing to specify each tenant individually.
    It iterates through all tenants, shows their migration state, and handles errors
    gracefully to ensure failures don't stop the display of other tenants.

    Features color-coded output for each tenant to make it easier to visually
    distinguish between different tenants' migration states.

    Inheritance:
        Inherits from django.core.management.base.BaseCommand, the base Django
        management command class.

    Key Functionality:
        - Discovers all tenants from database
        - Shows migration state for each tenant sequentially
        - Optionally filters by specific app
        - Catches exceptions per-tenant to continue with others
        - Provides detailed output per tenant
        - Uses tenant-specific backend for each tenant
        - Applies alternating colors for better visual separation

    Attributes:
        help (str): Help text shown in management command listing

    Color Scheme:
        Each tenant is assigned a color from a rotating palette:
        - Tenant 1: Cyan
        - Tenant 2: Yellow
        - Tenant 3: Green
        - Tenant 4: Magenta
        - Tenant 5: Blue
        (colors repeat after 5 tenants)

    Usage Examples:
        Show migrations for all tenants (with colors):
        ```bash
        $ python manage.py showmigrationsalltenants

        Tenant: acme (in cyan)
        ============
        admin
         [X] 0001_initial
         [X] 0002_logentry_remove_auto_add

        Tenant: beta (in yellow)
        ============
        admin
         [X] 0001_initial
         [X] 0002_logentry_remove_auto_add
        ```

    Notes:
        - No tenant_id argument (shows all tenants)
        - Useful for verifying migration consistency across tenants
        - Each tenant's state shown independently with distinct colors
        - Helps identify which tenants need migrations
        - Colors disabled with --no-color flag
    """

    help = "Show migration state for all tenants."

    # Define color rotation for tenants
    TENANT_COLORS = [
        "cyan",
        "yellow",
        "green",
        "magenta",
        "blue",
    ]

    def add_arguments(self, parser):
        """
        Add command-line arguments to the command parser.

        This method adds optional argument for app_label to filter migrations
        by specific app across all tenants.

        Arguments:
            parser (argparse.ArgumentParser): Django's argument parser for this command.

        Positional Arguments:
            app_label: App to show migrations for (optional, shows all if not specified)

        Django Arguments Inherited (from showmigrations command):
            --plan: Show migrations in plan format
            --verbosity: Output verbosity (0=silent, 1=normal, 2=verbose, 3=debug)
            --no-color: Disable colored output
            --database: Database alias (less relevant for tenant isolation)

        Examples:
            ```python
            # All tenants, all apps
            $ manage.py showmigrationsalltenants

            # All tenants, specific app
            $ manage.py showmigrationsalltenants users

            # With plan format
            $ manage.py showmigrationsalltenants --plan

            # With verbosity
            $ manage.py showmigrationsalltenants --verbosity=2

            # Without colors
            $ manage.py showmigrationsalltenants --no-color
            ```

        Notes:
            - app_label is optional
            - Parser is modified in-place
        """
        # Add positional argument for app_label
        parser.add_argument(
            "app_label",
            nargs="?",
            help="App label of the application to show migrations for.",
        )

        # Add --plan option (from Django's showmigrations)
        parser.add_argument(
            "--plan",
            action="store_true",
            help="Shows all migrations in the order they will be applied.",
        )

    def get_color_func(self, color_name):
        """
        Get a color function from Django's style system.

        Arguments:
            color_name (str): Name of the color (e.g., 'cyan', 'yellow', 'green')

        Returns:
            callable: Function that applies the color to text
        """
        # Map color names to Django style methods
        color_map = {
            "cyan": lambda x: f"\033[36m{x}\033[0m",  # Cyan
            "yellow": lambda x: f"\033[33m{x}\033[0m",  # Yellow
            "green": lambda x: f"\033[32m{x}\033[0m",  # Green
            "magenta": lambda x: f"\033[35m{x}\033[0m",  # Magenta
            "blue": lambda x: f"\033[34m{x}\033[0m",  # Blue
        }
        return color_map.get(color_name, lambda x: x)

    def handle(self, *args, **options):
        """
        Display migration state for all tenants with color-coded output.

        This method performs the following steps:
        1. Extracts app_label from options (if provided)
        2. Gets the Tenant model class
        3. Queries database for all tenant instances
        4. Iterates through each tenant sequentially
        5. For each tenant: Activates tenant context, assigns color, and shows migrations
        6. Catches and reports errors per-tenant
        7. Continues to next tenant even if current one fails

        Each tenant is assigned a color from a rotating palette to make the output
        easier to read and distinguish between different tenants.

        Arguments:
            *args: Positional arguments (typically empty, not used)
            **options (dict): Command options including:
                - app_label (str): Optional app to show migrations for
                - plan (bool): If True, show in plan format
                - verbosity (int): Output verbosity level (0-3, default 1)
                - no_color (bool): Whether to disable colored output
                - [other options]: Standard Django command options

        Returns:
            None: Django management commands don't return values. Output via stdout/stderr.
        """
        # Extract app_label from options
        app_label = options.pop("app_label", None)

        # Check if colors are disabled
        no_color = options.get("no_color", False)

        # Get the Tenant model class (can be customized via settings)
        Tenant = get_tenant_model()

        # Iterate through all tenants in database
        tenant_index = 0
        for tenant in Tenant.objects.all():  # type: ignore
            tenant: BaseTenant = tenant

            # Select color for this tenant (rotating through available colors)
            color_name = self.TENANT_COLORS[tenant_index % len(self.TENANT_COLORS)]
            color_func = self.get_color_func(color_name) if not no_color else lambda x: x
            tenant_index += 1

            # Display tenant header for clear separation (with bold and color)
            if not no_color:
                header = f"\n{'=' * 50}\nTenant: {tenant.tenant_id}\n{'=' * 50}"
                self.stdout.write(color_func(header))
            else:
                self.stdout.write(f"\n{'=' * 50}")
                self.stdout.write(f"Tenant: {tenant.tenant_id}")
                self.stdout.write("=" * 50)

            # Try to show migrations for this tenant, but continue if failure
            try:
                # Get the backend that knows how to access this tenant's database/schema
                backend = get_tenant_backend(tenant)

                # Activate tenant context (sets up database routing, schema, etc.)
                backend.activate()

                try:
                    # Build command arguments
                    cmd_args = []
                    if app_label:
                        cmd_args.append(app_label)

                    # If colors are enabled, wrap stdout to colorize all output
                    if not no_color:
                        original_stdout = sys.stdout
                        colored_stdout = ColoredOutput(self.stdout, color_func)
                        sys.stdout = colored_stdout

                    try:
                        # Call Django's showmigrations command within tenant context
                        call_command("showmigrations", *cmd_args, **options)
                    finally:
                        # Restore original stdout
                        if not no_color:
                            sys.stdout = original_stdout

                finally:
                    # Always deactivate tenant context, even if command fails
                    backend.deactivate()

            except Exception as e:
                # On failure, log error but continue to next tenant
                # This ensures one tenant's error doesn't prevent showing others
                self.stdout.write(self.style.ERROR(f"Failed to show migrations for tenant '{tenant.tenant_id}': {e}"))
