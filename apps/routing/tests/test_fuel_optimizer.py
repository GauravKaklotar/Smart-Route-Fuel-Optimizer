"""
Tests for FuelOptimizer.
"""

from decimal import Decimal
import pytest
from apps.routing.models import FuelStation
from apps.routing.services.station_locator import RouteStation
from apps.routing.services.fuel_optimizer import FuelOptimizer

def test_fuel_optimizer_short_route():
    optimizer = FuelOptimizer(mpg=10.0, max_gallons=50.0) # range 500 miles
    
    # 300 mile route needs no stops if start full
    stops = optimizer.optimize(300.0, [])
    assert len(stops) == 0

def test_fuel_optimizer_needs_stops():
    optimizer = FuelOptimizer(mpg=10.0, max_gallons=50.0)
    
    # 600 mile route. We must stop.
    # Put a station at 400 miles.
    station = FuelStation(truckstop_name="Midway", retail_price=Decimal("3.000"))
    route_station = RouteStation(station=station, distance_along_route_miles=400.0, distance_from_route_miles=0.1)
    
    stops = optimizer.optimize(600.0, [route_station])
    
    assert len(stops) == 1
    # At 400 miles, we have 10 gallons left (used 40).
    # We need to reach 600 miles (200 more miles = 20 gallons).
    # Since it's the only stop, we just fill up completely (or buy enough).
    # The algorithm says if no cheaper station ahead, fill up.
    # The destination dummy price is 0.0, which is cheaper!
    # So we should buy just enough to reach destination (20 gallons - 10 we have = 10 gallons to buy).
    assert stops[0].station.truckstop_name == "Midway"
    assert abs(stops[0].gallons_purchased - 10.0) < 0.001
    assert abs(stops[0].cost - 30.0) < 0.001
