"""
URL configuration for Spotter AI project.

Routes:
    /api/v1/         → Routing app API endpoints
    /api/schema/     → OpenAPI schema (JSON)
    /api/docs/       → Swagger UI
    /admin/          → Django admin
"""

from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/", include("apps.routing.api.urls")),
    # OpenAPI Schema & Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
