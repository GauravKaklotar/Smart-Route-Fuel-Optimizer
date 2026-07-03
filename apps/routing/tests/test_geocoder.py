"""
Tests for GeocodingService.
"""

from unittest.mock import patch
import pytest
from apps.routing.services.geocoder import GeocodingService
from apps.routing.services.exceptions import GeocodingError

@patch('requests.get')
def test_geocode_success(mock_get):
    # Mock ORS response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "features": [
            {
                "geometry": {
                    "coordinates": [-97.7431, 30.2672] # lon, lat
                }
            }
        ]
    }
    
    service = GeocodingService()
    lon, lat = service.geocode("Austin, TX, USA")
    
    assert lon == -97.7431
    assert lat == 30.2672
    mock_get.assert_called_once()

@patch('requests.get')
def test_geocode_no_results(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"features": []}
    
    service = GeocodingService()
    with pytest.raises(GeocodingError):
        service.geocode("Invalid Place")
