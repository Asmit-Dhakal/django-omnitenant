from rest_framework.serializers import ModelSerializer
from .models import Patient


class PatientSerializer(ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name']
        read_only_fields = ['id']

