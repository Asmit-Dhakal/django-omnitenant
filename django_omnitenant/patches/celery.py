from celery import Celery, Task
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_tenant_model


class TenantAwareTask(Task):
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
        tenant_id = None

        # Handle both styles: tenant_id in options OR inside kwargs
        if kwargs and "tenant_id" in kwargs:
            tenant_id = kwargs.pop("tenant_id")
        elif "tenant_id" in options:
            tenant_id = options.pop("tenant_id")

        if tenant_id:
            options.setdefault("headers", {})["tenant_id"] = tenant_id

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
        tenant_id = None
        headers = getattr(self.request, "headers", None)
        if headers:
            tenant_id = headers.get("tenant_id")

        if tenant_id:
            Tenant = get_tenant_model()
            tenant = Tenant.objects.get(tenant_id=tenant_id)
            with TenantContext.use_tenant(tenant):
                return super().__call__(*args, **kwargs)

        return super().__call__(*args, **kwargs)


Celery.Task = TenantAwareTask