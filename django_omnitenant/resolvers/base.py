class BaseTenantResolver:
    """
    Interface for resolving a tenant from a request.
    """

    def resolve(self, request):
        """
        Should return a Tenant instance or None.
        """
        raise NotImplementedError
