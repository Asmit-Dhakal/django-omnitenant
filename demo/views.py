from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from .models import Patient, Hospital
from .tasks import create_patient
from django.core.cache import cache


@api_view(["GET"])
def hospitals_view(request):
    """
    A simple API view that returns a list of hospitals.
    """
    hospitals = Hospital.objects.all()
    hospitals = [{"id": hospital.pk, "name": hospital.name} for hospital in hospitals]
    return Response(hospitals, status=status.HTTP_200_OK)


@api_view(["GET"])
def patients_view(request):
    """
    A simple API view that returns a list of patients.
    """
    result = cache.get("patients")
    if result is not None:
        return Response([{"id": patient.pk, "name": patient.name} for patient in result], status=status.HTTP_200_OK)
    patients = Patient.objects.all()
    cache.set("patients", patients)
    patients = [{"id": patient.pk, "name": patient.name} for patient in patients]
    return Response(patients, status=status.HTTP_200_OK)


@api_view(["POST"])
def create_patient_view(request):
    """
    A simple API view that creates a new patient.
    """
    name = request.data.get("name")
    if not name:
        return Response(
            {"error": "Name is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    patient = Patient.objects.create(name=name)
    return Response(
        {"id": patient.pk, "name": patient.name}, status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
def create_patient_async_view(request):
    """
    A simple API view that creates a new patient with the use of background workers.
    """
    name = request.data.get("name")
    if not name:
        return Response(
            {"error": "Name is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # create_patient.delay(name, tenant_id=request.tenant.tenant_id)
    create_patient.apply_async(kwargs={"name": name}, tenant_id=request.tenant.tenant_id) 
    return Response(
        {"detail": "Patient has been created successfully"}, status=status.HTTP_200_OK
    )
