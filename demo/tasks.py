# myapp/tasks.py
from celery import shared_task
from .models import Patient, Hospital
@shared_task
def add(x, y):
    return x + y

@shared_task
def create_patient(name):
    Patient.objects.create(name=name)


@shared_task
def get_hospitals():
    return list(Hospital.objects.all().values_list('name', flat=True))
