"""
Tests for API views.
"""

from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class RouteAPITests(APITestCase):

    def test_missing_fields_returns_400(self):
        url = reverse("routing:route-calculate")
        response = self.client.post(url, {"start": "Dallas, TX"}, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
        assert response.data["error"]["type"] == "validation_error"

    @patch("apps.routing.api.views.CacheService")
    @patch("apps.routing.api.views.GeocodingService")
    @patch("apps.routing.api.views.RoutingService")
    @patch("apps.routing.api.views.StationLocator")
    @patch("apps.routing.api.views.FuelOptimizer")
    def test_successful_route(
        self,
        mock_optimizer,
        mock_locator,
        mock_router,
        mock_geocoder,
        mock_cache,
    ):
        # Setup mocks
        mock_cache_instance = mock_cache.return_value
        mock_cache_instance.get_route.return_value = None
        
        mock_geocoder_instance = mock_geocoder.return_value
        mock_geocoder_instance.geocode.side_effect = [
            (-96.7970, 32.7767), # start
            (-87.6298, 41.8781)  # end
        ]
        
        # We don't need to deeply mock the returns of locator/router/optimizer
        # since we just want to ensure it calls them and returns a 200.
        # But we do need to mock ResponseBuilder implicitly or mock the outputs.
        # It's easier to patch the services so they return dummy data.
        
        class DummyRouteResult:
            distance_miles = 100.0
            duration_seconds = 3600.0
            encoded_polyline = "abc"
            coordinates_lonlat = [[-96.0, 32.0]]
            
        mock_router.return_value.get_route.return_value = DummyRouteResult()
        mock_locator.return_value.find_stations_near_route.return_value = []
        mock_optimizer.return_value.optimize.return_value = []

        url = reverse("routing:route-calculate")
        response = self.client.post(
            url,
            {"start": "Dallas, TX", "destination": "Chicago, IL"},
            format="json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["distance"] == 100.0
        assert response.data["total_fuel_cost"] == 0.0
        assert response.data["route"]["polyline"] == "abc"
        
        # Ensure it tried to cache the result
        mock_cache_instance.set_route.assert_called_once()
