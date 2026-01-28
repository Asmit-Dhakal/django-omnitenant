from django.apps import AppConfig

from .bootstrap import app_bootstrapper

class DjangoOmnitenantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_omnitenant'
    
    def ready(self):
        app_bootstrapper.run()
        # TODO: If default db engine is django.db.backends.postgresql.base then change it to django_omnitenant.backends.postgresql
        
