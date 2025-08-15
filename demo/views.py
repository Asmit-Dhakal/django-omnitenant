from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from .models import Patient



@api_view(["GET"])
def patients_view(request):
    """
    A simple API view that returns a list of patients.
    """
    patients = Patient.objects.all()
    patients = [{"id": patient.pk, "name": patient.name} for patient in patients]
    return Response(patients, status=status.HTTP_200_OK)


@api_view(["POST"])
def create_patient_view(request):
    """
    A simple API view that creates a new patient.
    """
    name = request.data.get("name")
    if not name:
        return Response({"error": "Name is required"}, status=status.HTTP_400_BAD_REQUEST)

    patient = Patient.objects.create(name=name)
    return Response({"id": patient.pk, "name": patient.name}, status=status.HTTP_201_CREATED)