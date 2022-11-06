from django.apps import AppConfig


class RubricsConfig(AppConfig):
    name = "rubrics"

    def ready(self) -> None:
        """Initializes signals for the app."""
        from . import signals
