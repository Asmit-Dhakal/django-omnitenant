import json
import logging

from django.core.management import call_command
from django.db import connections
from django.test import Client, TransactionTestCase

from django_omnitenant.conf import settings
from django_omnitenant.models import BaseTenant
from django_omnitenant.tenant_context import TenantContext
from django_omnitenant.utils import get_domain_model, get_tenant_model

logger = logging.getLogger(__name__)


class TenantAPITestCaseMixin:
    client_class = Client

    def _request(
        self,
        method: str,
        path: str,
        data=None,
        headers=None,
        content_type: str = "application/json",
        **kwargs,
    ):
        headers = headers or {}
        if method.lower() == "get":
            return self.client.get(path, data or {}, **headers, **kwargs)
        body = json.dumps(data or {}) if content_type == "application/json" else data
        return getattr(self.client, method)(
            path,
            body,
            content_type=content_type,
            **headers,
            **kwargs,
        )

    def get(self, path, data=None, headers=None, **kwargs):
        return self._request("get", path, data, headers, **kwargs)

    def post(
        self, path, data=None, headers=None, content_type="application/json", **kwargs
    ):
        return self._request("post", path, data, headers, content_type, **kwargs)

    def put(
        self, path, data=None, headers=None, content_type="application/json", **kwargs
    ):
        return self._request("put", path, data, headers, content_type, **kwargs)

    def patch(
        self, path, data=None, headers=None, content_type="application/json", **kwargs
    ):
        return self._request("patch", path, data, headers, content_type, **kwargs)

    def delete(self, path, data=None, headers=None, **kwargs):
        return self._request("delete", path, data, headers, **kwargs)


class BaseTenantTestCase(TransactionTestCase):
    tenant = None
    keepdb = True
    flush_per_test = False
    flush_per_class = True
    databases = {"default"}

    @classmethod
    def _setup_tenant(cls):
        raise NotImplementedError

    @classmethod
    def _remove_tenant(cls):
        if not cls.tenant:
            return
        try:
            cls.tenant.delete()
        except Exception as e:
            print(
                f"Error deleting tenant object '{cls.tenant}': {e}"
            )  # Use print for simplicity
        finally:
            cls.tenant = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._setup_tenant()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        tenant_ctx = getattr(cls, "_tenant_context", None)
        if tenant_ctx is not None:
            try:
                tenant_ctx.__exit__(None, None, None)
            except Exception as e:
                print(f"Error exiting tenant context: {e}")
            finally:
                cls._tenant_context = None
        cls._remove_tenant()
        super().tearDownClass()


class BaseAPITestCase(TenantAPITestCaseMixin, BaseTenantTestCase):
    domain = None

    @classmethod
    def _setup_domain(cls):
        if cls.domain is None:
            Domain = get_domain_model()
            cls.domain = Domain.objects.create(
                tenant=cls.tenant,
                domain=settings.DEFAULT_HOST,
            )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_domain()

    def setUp(self):
        super().setUp()
        self.client = self.client_class()


class DBTenantTestCase(BaseTenantTestCase):
    databases = {"default", "test_tenant"}  # Ensure non-default alias
    _db_alias = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._tenant_context = TenantContext.use_tenant(cls.tenant)
        cls._tenant_context.__enter__()
        if cls.flush_per_class and cls._db_alias:
            cls._flush_db(cls._db_alias)

    @classmethod
    def tearDownClass(cls):
        if not cls.keepdb and cls._db_alias:
            cls._destroy_db()
        super().tearDownClass()

    def tearDown(self):
        if self.keepdb and self.flush_per_test and self.__class__._db_alias:
            self._flush_db(self.__class__._db_alias)
        super().tearDown()

    @classmethod
    def _setup_tenant(cls):
        if cls.tenant is None:
            Tenant = get_tenant_model()
            cls.tenant = Tenant.objects.create(
                name="Test Tenant",
                tenant_id="test_db_tenant",
                isolation_type=BaseTenant.IsolationType.DATABASE,
            )
        cls._db_alias = cls._get_db_alias()
        if cls._db_alias not in cls.databases:
            cls.databases = set(cls.databases) | {cls._db_alias}
        conn = connections[cls._db_alias]
        conn.creation.create_test_db(
            autoclobber=True, serialize=False, keepdb=cls.keepdb
        )

    @classmethod
    def _destroy_db(cls):
        conn = connections[cls._db_alias]
        try:
            conn.close()
            conn.creation.destroy_test_db(cls._db_alias, verbosity=0)
        finally:
            cls._db_alias = None
            cls.databases = {"default"}

    @classmethod
    def _get_db_alias(cls):
        db_alias = next((db for db in cls.databases if db != "default"), "test_tenant")
        config = cls.tenant.config.get("db_config", {})
        config["NAME"] = db_alias
        cls.tenant.config["db_config"] = config
        cls.tenant.save()
        return db_alias

    @staticmethod
    def _flush_db(db_alias):
        call_command("flush", verbosity=0, interactive=False, database=db_alias)


class DBTenantAPITestCase(BaseAPITestCase, DBTenantTestCase):
    pass


class SchemaTenantTestCase(BaseTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.flush_per_class:
            cls._flush_schema()
        with TenantContext.use_tenant(cls.tenant):  # Run migrations in tenant context
            call_command("migrate", verbosity=0, interactive=False)

    def setUp(self) -> None:
        super().setUp()
        self._tenant_context = TenantContext.use_tenant(self.tenant)
        self._tenant_context.__enter__()

    def tearDown(self):
        if hasattr(self, "_tenant_context") and self._tenant_context is not None:
            self._tenant_context.__exit__(None, None, None)
            self._tenant_context = None
        super().tearDown()

    @classmethod
    def _setup_tenant(cls):
        if cls.tenant is None:
            Tenant = get_tenant_model()
            cls.tenant = Tenant.objects.create(
                name="Test Schema Tenant",
                tenant_id="test_schema_tenant",
                isolation_type=BaseTenant.IsolationType.SCHEMA,
            )

    @classmethod
    def _flush_schema(cls):
        with TenantContext.use_tenant(cls.tenant):
            call_command("flush", verbosity=0, interactive=False, database="default")


class SchemaTenantAPITestCase(BaseAPITestCase, SchemaTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with TenantContext.use_schema(settings.PUBLIC_SCHEMA_NAME):
            cls._setup_domain()
