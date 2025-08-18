from django.contrib import admin

from .models import Hospital, Domain, Patient

admin.site.register(Hospital)
admin.site.register(Domain)
admin.site.register(Patient)
