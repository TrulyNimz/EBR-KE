from django.apps import AppConfig


class SchemaManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.schema_manager'
    verbose_name = 'Dynamic Schema Manager'
