"""
Tests for CSV import management command.
"""

import os
import tempfile
from unittest.mock import patch
import pytest
from django.core.management import call_command
from apps.routing.models import FuelStation

@pytest.fixture
def sample_csv():
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, 'w') as f:
        f.write("OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price\n")
        f.write("1001,Stop A,123 Main,Austin,TX,1,3.250\n")
        f.write("1002,Stop B,456 Oak,Dallas,TX,2,3.100\n")
        # Invalid row (missing price)
        f.write("1003,Stop C,789 Elm,Houston,TX,3,\n")
    yield path
    os.remove(path)

@pytest.mark.django_db
def test_import_csv_command(sample_csv):
    # Ensure empty db
    assert FuelStation.objects.count() == 0
    
    # Run command
    call_command('import_csv', file=sample_csv)
    
    # Check results (2 valid rows should be imported)
    assert FuelStation.objects.count() == 2
    
    station_a = FuelStation.objects.get(opis_id="1001")
    assert station_a.truckstop_name == "Stop A"
    assert station_a.city == "Austin"
    assert float(station_a.retail_price) == 3.250
