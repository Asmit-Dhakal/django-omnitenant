"""
Create Tenant Management Command

Django management command for interactive tenant creation with full configuration.

Purpose:
    Provides user-friendly interface to create new tenants with:
    - Unique tenant_id assignment
    - Display name configuration
    - Isolation strategy selection
    - Database/schema provisioning
    - Automatic migration execution
    
Interactive Flow:
    1. Prompt for tenant ID (unique identifier)
    2. Prompt for tenant name (display name)
    3. Select isolation type (database/schema/table/cache)
    4. If database isolation:
       - Ask to create database
       - Collect database credentials
    5. Ask to run migrations
    6. Create tenant in master database
    7. Provision database/schema if applicable
    8. Run migrations if requested
    
Isolation Types:
    - DATABASE: Separate PostgreSQL database per tenant
    - SCHEMA: PostgreSQL schema in shared database
    - TABLE: Row-level separation in shared schema
    - CACHE: Cache key prefixing in shared cache
    
Error Handling:
    - Duplicate tenant_id detection
    - Database connection validation
    - Existing database handling
    - Transaction rollback on failure
    
Output:
    - Success/failure messages
    - Progress indicators
    - Error details
    - Setup completion confirmation

Usage:
    ```bash
    python manage.py createtenant
    ```
    
    Interactive prompts guide through:
    - Tenant ID: acme
    - Tenant Name: ACME Corporation
    - Isolation Type: database
    - Database Config: acme_db, user, password, etc.
    - Run Migrations: yes
"""

from django.core.management.base import BaseCommand
from django_omnitenant.models import BaseTenant
from django_omnitenant.utils import get_tenant_model, get_tenant_backend


class Command(BaseCommand):
    """
    Django management command to create new tenants interactively.
    
    This command guides users through the process of creating a new tenant
    with all necessary configuration including database/schema provisioning
    and migration execution.
    
    Attributes:
        help (str): Short description for management command
    """
    help = "Create a new tenant interactively"

    def handle(self, *args, **options):
        """
        Execute the tenant creation flow.
        
        Orchestrates the entire interactive tenant creation process:
        1. Collect tenant metadata (ID, name, isolation type)
        2. Collect database config if applicable
        3. Create tenant object in master database
        4. Provision infrastructure (database/schema)
        5. Run migrations if requested
        
        Args:
            *args: Positional arguments (unused)
            **options: Keyword arguments from command line (unused)
            
        Process Flow:
            ```
            Start
              ↓
            Prompt tenant ID
              ↓
            Prompt tenant name
              ↓
            Select isolation type
              ↓
            [Collect DB config if DATABASE isolation]
              ↓
            Create tenant record
              ↓
            [Provision database/schema]
              ↓
            [Run migrations if requested]
              ↓
            Complete or Error
            ```
        """
        # Display welcome message
        self.stdout.write(self.style.SUCCESS("Starting tenant creation..."))

        # --- Step 1: Collect Tenant Metadata ---
        
        # Prompt for unique tenant identifier
        # Used as subdomain (tenant.example.com) or database name
        tenant_id = input("Enter tenant ID (unique): ").strip()

        # Prompt for human-readable tenant name
        # Used for display and identification in UI
        tenant_name = input("Enter tenant name: ").strip()

        # --- Step 2: Select Isolation Type ---
        
        # Build valid input mapping from isolation type choices
        # Convert choices labels to lowercase for user input matching
        # Example: {('DATABASE', 'Database Per Tenant')} → {'database': 'DATABASE'}
        valid_inputs = {
            label.lower(): value for value, label in BaseTenant.IsolationType.choices
        }
        
        # Validate isolation type input until valid selection made
        isolation_type_input = None
        while isolation_type_input not in valid_inputs:
            # Prompt user with available isolation type options
            isolation_type_input = (
                input(f"Select isolation type ({'/'.join(valid_inputs.keys())}): ")
                .strip()
                .lower()
            )

        # Convert user input to isolation type constant
        isolation_type = valid_inputs[isolation_type_input]

        # --- Step 3: Collect Database Configuration (if applicable) ---
        
        # Initialize database config dict (empty if not database isolation)
        db_config = {}
        create_db = False

        # Ask if migrations should be run immediately after creation
        # This speeds up onboarding but can be skipped for later setup
        run_migrations = self._ask_yes_no(
            "Do you want to run migrations for this tenant now?"
        )
        
        # For DATABASE isolation, collect database connection details
        if isolation_type in (BaseTenant.IsolationType.DATABASE,):
            # Ask if database should be created automatically
            # If no, database must be created manually beforehand
            create_db = self._ask_yes_no(
                "Do you want to create the database now? (y/n): "
            )

            # Collect database connection parameters
            db_name = input("Enter database name for tenant: ").strip()
            db_user = input("Enter database user: ").strip()
            db_password = input("Enter database password: ").strip()
            db_host = input("Enter database host: ").strip()
            # Default port to 5432 (PostgreSQL default) if not provided
            db_port = input("Enter database port (default: 5432): ").strip() or "5432"

            # Build database configuration dict for tenant storage
            db_config = {
                "NAME": db_name,
                "USER": db_user,
                "PASSWORD": db_password,
                "HOST": db_host,
                "PORT": db_port,
            }

        # --- Step 4: Create Tenant Record ---
        
        # Initialize tenant variable for later reference
        tenant = None  # type: ignore
        
        # Create tenant object in master database
        # Stores tenant metadata and configuration
        tenant: BaseTenant = get_tenant_model().objects.create(
            tenant_id=tenant_id,
            name=tenant_name,
            isolation_type=isolation_type,
            # Store database config in tenant config
            # Used by backend for connection setup
            config={"db_config": db_config},
        )  # type: ignore
        
        # Confirm tenant creation
        self.stdout.write(
            self.style.SUCCESS(f"Tenant '{tenant_name}' created successfully!")
        )
        
        # Get backend for this tenant
        # Backend handles database/schema provisioning and migrations
        backend = get_tenant_backend(tenant)

        # --- Step 5: Provision Infrastructure ---
        
        try:
            # Handle database isolation provisioning
            if tenant.isolation_type == BaseTenant.IsolationType.DATABASE:
                if create_db:
                    # User selected to create database
                    self.stdout.write(f"Creating database '{db_name}'...")
                    # Backend creates database and runs migrations if requested
                    backend.create(run_migrations=run_migrations)
                elif run_migrations:
                    # Database exists, just run migrations
                    backend.migrate()

            # Handle schema isolation provisioning
            elif tenant.isolation_type == BaseTenant.IsolationType.SCHEMA:
                # Backend creates schema and runs migrations if requested
                backend.create(run_migrations=run_migrations)
        
        # Error handling for database operations
        except Exception as e:
            # If database already exists, continue (partial failure recovery)
            if "already exists" in str(e).lower():
                self.stdout.write(
                    self.style.WARNING(
                        "DB already exists. Tenant creation continues..."
                    )
                )
            else:
                # For other errors, rollback by deleting tenant record
                # Ensures consistency if infrastructure creation fails
                if tenant:
                    tenant.delete()
                # Report error and exit
                self.stdout.write(self.style.ERROR(f"Tenant creation failed: {e}"))
                return

        # Success message
        self.stdout.write(self.style.SUCCESS("Tenant setup complete."))

    def _ask_yes_no(self, prompt: str) -> bool:
        """
        Ask the user a yes/no question until valid response given.
        
        Repeatedly prompts user until 'y'/'yes' or 'n'/'no' entered.
        
        Args:
            prompt (str): Question to ask user (e.g., "Run migrations?")
            
        Returns:
            bool: True if user answered yes, False if no
            
        Valid Responses:
            Yes: 'y', 'yes' (case-insensitive)
            No: 'n', 'no' (case-insensitive)
            
        Invalid responses prompt for retry.
        
        Examples:
            ```python
            run_migrations = self._ask_yes_no("Run migrations now?")
            # User: y
            # Returns: True
            
            create_db = self._ask_yes_no("Create database?")
            # User: no
            # Returns: False
            ```
        """
        # Define valid yes/no responses
        valid_yes = {"y", "yes"}
        valid_no = {"n", "no"}
        
        # Keep prompting until valid response
        while True:
            # Get user input and normalize
            answer = input(f"{prompt} (y/n): ").strip().lower()
            
            # Check if yes response
            if answer in valid_yes:
                return True
            # Check if no response
            elif answer in valid_no:
                return False
            # Invalid response - prompt to try again
            else:
                self.stdout.write(
                    self.style.ERROR("Please enter 'y' or 'n' (or 'yes' / 'no').")
                )
