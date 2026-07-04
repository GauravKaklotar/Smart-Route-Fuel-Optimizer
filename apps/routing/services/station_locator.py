"""
Station locator service using spatial indexing (BallTree) and Shapely geometries.
"""

import math
from typing import List, Tuple
from dataclasses import dataclass

import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import transform
from sklearn.neighbors import BallTree

from apps.routing.models import FuelStation
from apps.routing.services.constants import (
    BUFFER_DISTANCE_MILES,
    EARTH_RADIUS_MILES,
    EPSG_CONUS,
    EPSG_WGS84,
)
from apps.routing.services.exceptions import RoutingError


@dataclass
class RouteStation:
    """A fuel station projected onto the route with its distance along the route."""
    station: FuelStation
    distance_along_route_miles: float
    distance_from_route_miles: float


class StationLocator:
    """Finds fuel stations near a given route using BallTree spatial indexing."""

    def __init__(self) -> None:
        # Load all geocoded stations from DB
        self.stations = list(
            FuelStation.objects.filter(latitude__isnull=False, longitude__isnull=False)
        )
        
        if not self.stations:
            self.ball_tree = None
            return

        # Prepare BallTree
        # BallTree haversine metric requires coordinates in radians (lat, lon)
        coords = np.array([
            [math.radians(s.latitude), math.radians(s.longitude)]
            for s in self.stations
        ])
        
        # Build the tree
        self.ball_tree = BallTree(coords, metric="haversine")

        # Setup transformers for buffering
        # Always use (lon, lat) ordering for WGS84 when using PyProj 2+ with always_xy=True
        self.project_to_meters = Transformer.from_crs(
            EPSG_WGS84, EPSG_CONUS, always_xy=True
        ).transform
        self.project_to_wgs84 = Transformer.from_crs(
            EPSG_CONUS, EPSG_WGS84, always_xy=True
        ).transform

    def find_stations_near_route(
        self, 
        route_coords_lonlat: List[Tuple[float, float]], 
        buffer_miles: float = BUFFER_DISTANCE_MILES
    ) -> List[RouteStation]:
        """
        Finds and returns fuel stations within the buffer distance of the route,
        sorted by their projected distance along the route.

        Args:
            route_coords_lonlat: List of (lon, lat) tuples making up the route.
            buffer_miles: How far from the route to look for stations.

        Returns:
            List of RouteStation objects sorted by distance along the route.
        """
        if not self.ball_tree or not self.stations:
            return []

        if len(route_coords_lonlat) < 2:
            raise RoutingError("Route must have at least 2 points.")

        # 1. Create a LineString in WGS84
        route_line = LineString(route_coords_lonlat)

        # 2. To get a tight bounding box/buffer for the BallTree query, we should sample
        # points along the route and query them, or we can query the BallTree for points 
        # within the buffer radius of all points on the route line.
        # But a more efficient way for large routes is to query points every X miles.
        # Alternatively, we can project to 5070, buffer, back to 4326, get bounds, 
        # filter stations in bounds, then precise check.
        # Given we have 10k stations, BallTree query per route point is fast enough.
        
        # Let's optimize: reduce route points by simplifying, then query BallTree for each point
        # with radius = buffer_miles.
        # Simplify the route to reduce points (e.g. 0.01 degrees ~ 0.5 miles)
        simplified_line = route_line.simplify(0.01, preserve_topology=False)
        
        # Radius in radians for BallTree
        radius_radians = (buffer_miles * 2) / EARTH_RADIUS_MILES
        
        # Query BallTree for all points in simplified line
        query_points = np.array([
            [math.radians(lat), math.radians(lon)]
            for lon, lat in simplified_line.coords
        ])
        
        # indices of stations near any of the points
        indices = self.ball_tree.query_radius(query_points, r=radius_radians)
        
        # Flatten and unique the indices
        unique_indices = set()
        for ind_array in indices:
            unique_indices.update(ind_array)
            
        candidate_stations = [self.stations[i] for i in unique_indices]
        
        if not candidate_stations:
            return []

        # 3. For the candidates, do a precise check using Shapely's distance to the exact route line
        # To do this accurately, we project the line to a metric CRS (EPSG:5070)
        route_line_meters = transform(self.project_to_meters, route_line)
        buffer_meters = buffer_miles * 1609.344
        
        results = []
        for station in candidate_stations:
            point_wgs84 = Point(station.longitude, station.latitude)
            point_meters = transform(self.project_to_meters, point_wgs84)
            
            # Distance from the route line in meters
            dist_from_route_meters = route_line_meters.distance(point_meters)
            
            if dist_from_route_meters <= buffer_meters:
                # Distance along the route from the start (project returns distance along the line)
                dist_along_route_meters = route_line_meters.project(point_meters)
                
                results.append(
                    RouteStation(
                        station=station,
                        distance_along_route_miles=dist_along_route_meters / 1609.344,
                        distance_from_route_miles=dist_from_route_meters / 1609.344,
                    )
                )

        # 4. Sort by distance along the route
        results.sort(key=lambda x: x.distance_along_route_miles)
        return results
