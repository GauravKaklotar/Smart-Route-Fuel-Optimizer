"""
URL routing for the API endpoints.
"""

from django.urls import path
from apps.routing.api.views import RouteView

app_name = "routing"

urlpatterns = [
    path("routes/", RouteView.as_view(), name="route-calculate"),
]
