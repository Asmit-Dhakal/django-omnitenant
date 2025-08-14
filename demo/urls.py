from django.urls import path
from .views import patients_view, create_patient_view

urlpatterns = [
    path('patients/', patients_view, name='patients_view'),
    path('patients/create/', create_patient_view, name='create_patient_view'),
]
