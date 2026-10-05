from django.apps import AppConfig
class CoreConfig(AppConfig):
    name='core'
    verbose_name='Сайт и контент'
    def ready(self):
        from . import signals
