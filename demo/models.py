from django.db import models
from django_omnitenant.models import BaseTenant
# Create your models here.


class Hospital(BaseTenant):

    def __str__(self) -> str:
        return self.name

class Patient(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name