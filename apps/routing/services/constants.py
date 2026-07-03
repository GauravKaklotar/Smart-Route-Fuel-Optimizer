"""
Constants for the routing engine.
"""

# Vehicle assumptions from requirements
VEHICLE_RANGE_MILES = 500.0
FUEL_EFFICIENCY_MPG = 10.0

# Start with full tank capacity (gallons)
# 500 miles / 10 MPG = 50 gallons
MAX_FUEL_GALLONS = VEHICLE_RANGE_MILES / FUEL_EFFICIENCY_MPG

# Distance buffer for nearby stations (miles)
BUFFER_DISTANCE_MILES = 5.0

# Earth radius in miles (for haversine calculations)
EARTH_RADIUS_MILES = 3959.0

# Metres to Miles conversion factor
METERS_PER_MILE = 1609.344

# Projections
EPSG_WGS84 = "EPSG:4326"       # Global lat/lon
EPSG_CONUS = "EPSG:5070"       # CONUS Albers Equal Area (meters)
