"""
Tests for routing app models.
"""

from decimal import Decimal
import pytest
from apps.routing.models import FuelStation

@pytest.mark.django_db
def test_fuel_station_creation():
    station = FuelStation.objects.create(
        opis_id="123",
        truckstop_name="Test Stop",
        address="123 Main St",
        city="Testville",
        state="TX",
        retail_price=Decimal("3.500")
    )
    assert station.opis_id == "123"
    assert station.city == "Testville"
    assert str(station) == "Test Stop (Testville, TX) - $3.500"
