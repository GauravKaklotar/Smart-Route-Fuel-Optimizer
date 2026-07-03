"""
Tests for StationLocator.
"""

import pytest
from apps.routing.models import FuelStation
from apps.routing.services.station_locator import StationLocator, RouteStation

@pytest.mark.django_db
def test_station_locator_finds_stations():
    # Create stations with coordinates
    s1 = FuelStation.objects.create(opis_id="1", truckstop_name="S1", city="A", state="TX", retail_price=3.0, latitude=30.0, longitude=-97.0)
    # This one is far away
    s2 = FuelStation.objects.create(opis_id="2", truckstop_name="S2", city="B", state="TX", retail_price=3.0, latitude=35.0, longitude=-100.0)
    
    locator = StationLocator()
    
    # Route passing right through s1
    route_coords = [(-97.0, 29.9), (-97.0, 30.1)]
    
    stations = locator.find_stations_near_route(route_coords, buffer_miles=5.0)
    
    assert len(stations) == 1
    assert stations[0].station.opis_id == "1"
    assert stations[0].distance_from_route_miles < 5.0
