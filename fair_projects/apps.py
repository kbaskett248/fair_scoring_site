from django.apps import AppConfig


class FairProjectsConfig(AppConfig):
    name = 'fair_projects'
    verbose_name = 'Fair Projects'

    def ready(self):
        from . import signals
