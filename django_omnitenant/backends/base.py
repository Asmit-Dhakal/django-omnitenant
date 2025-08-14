from django_omnitenant.models import BaseTenant


class BaseTenantBackend:
    def __init__(self, tenant):
        self.tenant: BaseTenant = tenant

    def bind(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def migrate(self):
        raise NotImplementedError

    def activate(self):
        raise NotImplementedError

    def deactivate(self):
        raise NotImplementedError
