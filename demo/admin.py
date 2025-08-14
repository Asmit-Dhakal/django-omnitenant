from django.contrib import admin

from .models import Hospital, Patient

admin.site.register(Hospital)
admin.site.register(Patient)
