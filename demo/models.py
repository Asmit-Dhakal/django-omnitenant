from django.db import models
from django_omnitenant.models import BaseTenant, BaseDomain
# Create your models here.


class Hospital(BaseTenant):
    tenant_managed = False

    def __str__(self) -> str:
        return self.name
 
class Domain(BaseDomain):
    tenant_managed = False

    def __str__(self) -> str:
        return self.domain
    
   

class Patient(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name