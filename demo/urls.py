from django.urls import path
from .views import patients_view, create_patient_view, hospitals_view, create_patient_async_view

urlpatterns = [
    path('hospitals/', hospitals_view, name='hospital-list'),
    path('patients/', patients_view, name='patient-list'),
    path('patients/create/', create_patient_view, name='patient-create'),
    path('patients/create_async/', create_patient_async_view, name='patient-create-async'),
]
