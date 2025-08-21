from django_omnitenant.signals import (
    tenant_created,
    tenant_migrated,
    tenant_deleted,
    tenant_activated,
    tenant_deactivated,
)


class BaseTenantBackend:
    def __init__(self, tenant):
        self.tenant = tenant

    def create(self, run_migrations=False):
        """Provision tenant resources (DB/schema/etc)."""
        self.bind()
        tenant_created.send(sender=self.tenant.__class__, tenant=self.tenant)
        if run_migrations:
            self.migrate()

    def delete(self):
        """Tear down tenant resources (DB/schema/etc)."""
        tenant_deleted.send(sender=self.tenant.__class__, tenant=self.tenant)

    def migrate(self, *args, **kwargs):
        """Run tenant-specific migrations."""
        tenant_migrated.send(sender=self.tenant.__class__, tenant=self.tenant)

    def bind(self):
        """Attach tenant resources (DB/schema/etc) to Django settings."""
        raise NotImplementedError

    def activate(self):
        tenant_activated.send(sender=self.tenant.__class__, tenant=self.tenant)

    def deactivate(self):
        tenant_deactivated.send(sender=self.tenant.__class__, tenant=self.tenant)
