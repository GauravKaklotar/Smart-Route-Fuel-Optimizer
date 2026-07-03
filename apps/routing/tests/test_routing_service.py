"""
Tests for RoutingService.
"""

from unittest.mock import patch
import pytest
from apps.routing.services.routing_service import RoutingService
from apps.routing.services.exceptions import RoutingError

@patch('requests.post')
def test_get_route_success(mock_post):
    # Mock ORS V2 Directions response
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "routes": [
            {
                "summary": {
                    "distance": 160934.4, # 100 miles in meters
                    "duration": 3600 # 1 hour
                },
                "geometry": "gfo}Eto_xO~`@e^" # some polyline
            }
        ]
    }
    
    service = RoutingService()
    result = service.get_route((-97.7, 30.2), (-96.7, 32.7)) # lon, lat
    
    assert abs(result.distance_miles - 100.0) < 0.1
    assert result.duration_seconds == 3600
    assert result.encoded_polyline == "gfo}Eto_xO~`@e^"
    assert len(result.coordinates_lonlat) > 0

@patch('requests.post')
def test_get_route_no_routes(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"routes": []}
    
    service = RoutingService()
    with pytest.raises(RoutingError):
        service.get_route((-97.0, 30.0), (-96.0, 31.0))
