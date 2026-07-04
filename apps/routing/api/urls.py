"""
URL routing for the API endpoints.
"""

from django.urls import path
from apps.routing.api.views import RouteView, HealthCheckView, SearchLocationsView, FuelPricesView  

app_name = "routing"

urlpatterns = [
    # Main route calculation
    path("routes/", RouteView.as_view(), name="route-calculate"),

    # Health check
    path("health/", HealthCheckView.as_view(), name="health-check"),
    
    # Search locations
    path("search/", SearchLocationsView.as_view(), name="search-locations"),
    
    # Fuel prices
    path("prices/", FuelPricesView.as_view(), name="fuel-prices"),
]
