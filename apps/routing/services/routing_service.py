"""
Routing service using OpenRouteService Directions API.
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple

import polyline
import requests
from django.conf import settings

from apps.routing.services.constants import METERS_PER_MILE
from apps.routing.services.exceptions import RoutingError

logger = logging.getLogger(__name__)


@dataclass
class RouteResult:
    """Structured result from the routing service."""
    distance_miles: float
    duration_seconds: float
    encoded_polyline: str
    coordinates_lonlat: List[Tuple[float, float]]


class RoutingService:
    """Service to handle route calculation via OpenRouteService."""

    def __init__(self) -> None:
        self.api_key = settings.ORS_API_KEY
        self.base_url = settings.ORS_BASE_URL.rstrip("/")
        if not self.api_key:
            logger.warning("ORS_API_KEY is not set. Routing will fail.")

    def get_route(
        self, origin_lonlat: Tuple[float, float], destination_lonlat: Tuple[float, float]
    ) -> RouteResult:
        """
        Calculates a driving route between two points.

        Args:
            origin_lonlat: (longitude, latitude) of start.
            destination_lonlat: (longitude, latitude) of end.

        Returns:
            RouteResult containing distance, duration, polyline, and decoded coords.

        Raises:
            RoutingError: If the route calculation fails.
        """
        url = f"{self.base_url}/v2/directions/driving-car"
        
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8"
        }
        
        payload = {
            "coordinates": [
                [origin_lonlat[0], origin_lonlat[1]],
                [destination_lonlat[0], destination_lonlat[1]]
            ],
            "units": "m",
            "instructions": False
        }

        try:
            # Note: ORS V2 API expects POST with json payload
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error("ORS Routing API error: %s", str(e))
            # Try to extract a more meaningful error from ORS JSON if available
            error_message = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    err_data = e.response.json()
                    if "error" in err_data:
                        error_message = f"{err_data['error'].get('message', 'Unknown error')} (Code: {err_data['error'].get('code', 'N/A')})"
                except Exception:
                    pass
            raise RoutingError(f"Failed to calculate route: {error_message}") from e
        except ValueError as e:
            raise RoutingError("Invalid JSON response from routing service.") from e

        routes = data.get("routes", [])
        if not routes:
            raise RoutingError("No route found between the specified locations.")

        route = routes[0]
        summary = route.get("summary", {})
        
        # Distance in meters, duration in seconds
        distance_meters = summary.get("distance", 0)
        duration_seconds = summary.get("duration", 0)
        
        distance_miles = distance_meters / METERS_PER_MILE
        
        encoded_polyline = route.get("geometry", "")
        if not encoded_polyline:
            raise RoutingError("Route geometry is missing.")

        # Decode polyline. The polyline package returns (lat, lon) by default.
        # We need to map it back to (lon, lat) to be consistent with our GeoJSON-like usage.
        coords_latlon = polyline.decode(encoded_polyline, 5) # ORS uses precision 5 by default
        coords_lonlat = [(lon, lat) for lat, lon in coords_latlon]

        return RouteResult(
            distance_miles=distance_miles,
            duration_seconds=duration_seconds,
            encoded_polyline=encoded_polyline,
            coordinates_lonlat=coords_lonlat
        )
