from django.apps import AppConfig


class PersistenceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.infrastructure.persistence'
    label = 'persistence'
    verbose_name = 'Управление Канбан-системой'

    def ready(self):
        import backend.infrastructure.persistence.signals  # noqa
