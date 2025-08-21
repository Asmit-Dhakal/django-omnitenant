from django.dispatch import Signal

# Sent after a tenant is created (schema/db is set up)
tenant_created = Signal()

# Sent after a tenant is deleted (schema/db is torn down)
tenant_deleted = Signal()


tenant_migrated = Signal()

# Optional: Sent when tenant context is entered/exited
tenant_activated = Signal()
tenant_deactivated = Signal()
