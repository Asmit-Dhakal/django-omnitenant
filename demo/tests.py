from django_omnitenant.tests import (
    DBTenantTestCase,
    DBTenantAPITestCase,
    SchemaTenantTestCase,
    SchemaTenantAPITestCase,
)
from demo.models import Patient
from django.urls import reverse


class TestPatient(DBTenantTestCase):
    """
    Test case for the Patient model in a tenant context.
    """

    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(name="John Doe")

    def tearDown(self):
        super().tearDown()
        self.patient.delete()

    def test_patient_creation(self):
        self.assertIsNotNone(self.patient.pk)
        self.assertEqual(self.patient.name, "John Doe")

    def test_patient_tenant_association(self):
        patients = Patient.objects.filter(name=self.patient.name)
        self.assertIn(self.patient, patients)


class TestPatientAPI(DBTenantAPITestCase):
    """
    Test case for the Patient API in a tenant context.
    """

    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(name="Jane Doe")

    def test_patient_api_get(self):
        response = self.client.get(reverse("patient-list"))
        self.assertEqual(response.status_code, 200)
        data: list[dict] = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], self.patient.name)

    def test_patient_api_create(self):
        response = self.client.post(reverse("patient-create"), {"name": "Alice"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "Alice")


class SchemaTestPatient(SchemaTenantTestCase):
    """
    Test case for the Patient model in a tenant context.
    """

    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(name="John Doe")

    def test_patient_creation(self):
        self.assertIsNotNone(self.patient.pk)
        self.assertEqual(self.patient.name, "John Doe")

    def test_patient_tenant_association(self):
        patients = Patient.objects.filter(name=self.patient.name)
        self.assertIn(self.patient, patients)


class SchemaTestPatientAPI(SchemaTenantAPITestCase):
    """
    Test case for the Patient API in a tenant context.
    """

    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(name="Jane Doe")

    def tearDown(self):
        self.patient.delete()
        super().tearDown()

    def test_patient_api_get(self):
        response = self.client.get(reverse("patient-list"))
        self.assertEqual(response.status_code, 200)
        data: list[dict] = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], self.patient.name)

    def test_patient_api_create(self):
        response = self.client.post(reverse("patient-create"), {"name": "Alice"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "Alice")
