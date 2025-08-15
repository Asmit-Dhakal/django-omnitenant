from django.urls import path
from .views import patients_view, create_patient_view, hospitals_view

urlpatterns = [
    path('hospitals/', hospitals_view, name='hospitals_view'),
    path('patients/', patients_view, name='patients_view'),
    path('patients/create/', create_patient_view, name='create_patient_view'),
]
