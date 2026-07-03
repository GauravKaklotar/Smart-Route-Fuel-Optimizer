"""
Response builder for formatting API output.
"""

from typing import Any, Dict, List

from apps.routing.services.fuel_optimizer import FuelStop
from apps.routing.services.routing_service import RouteResult


class ResponseBuilder:
    """Assembles the final API response dictionary."""

    def build(
        self,
        route_result: RouteResult,
        fuel_stops: List[FuelStop]
    ) -> Dict[str, Any]:
        """
        Builds the structured JSON response.

        Args:
            route_result: Result from routing service.
            fuel_stops: Result from fuel optimizer.

        Returns:
            Dictionary matching the API specification.
        """
        total_fuel_cost = sum(stop.cost for stop in fuel_stops)

        formatted_stops = []
        for stop in fuel_stops:
            formatted_stops.append({
                "opis_id": stop.station.opis_id,
                "name": stop.station.truckstop_name,
                "location": f"{stop.station.city}, {stop.station.state}",
                "retail_price": float(stop.station.retail_price),
                "gallons_purchased": round(stop.gallons_purchased, 3),
                "cost": round(stop.cost, 2),
                "coordinates": {
                    "latitude": stop.station.latitude,
                    "longitude": stop.station.longitude,
                }
            })

        return {
            "distance": round(route_result.distance_miles, 2),
            "duration": round(route_result.duration_seconds, 2),
            "total_fuel_cost": round(total_fuel_cost, 2),
            "fuel_stops": formatted_stops,
            "route": {
                "polyline": route_result.encoded_polyline,
                # Convert list of tuples to list of dicts for clearer JSON, or array of arrays
                # The spec says "coordinates": [...]
                # We'll use [lon, lat] arrays to be standard GeoJSON-like
                "coordinates": [[lon, lat] for lon, lat in route_result.coordinates_lonlat]
            }
        }
