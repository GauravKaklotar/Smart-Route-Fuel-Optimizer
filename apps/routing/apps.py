from django.apps import AppConfig


class RoutingConfig(AppConfig):
    """Configuration for the routing application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.routing"
    verbose_name = "Fuel Route Optimization"
