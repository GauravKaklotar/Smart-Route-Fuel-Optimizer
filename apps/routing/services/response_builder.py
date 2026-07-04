"""
Response builder for formatting API output.
"""

from typing import Any, Dict, List

from apps.routing.services.fuel_optimizer import FuelStop
from apps.routing.services.routing_service import RouteResult


class ResponseBuilder:
    """Assembles the final API response dictionary."""

    def _format_duration(self, seconds: float) -> str:
        """Format duration as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

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
        total_gallons = sum(stop.gallons_purchased for stop in fuel_stops)

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
            "trip_summary": {
                "distance_miles": round(route_result.distance_miles, 2),
                "duration_seconds": round(route_result.duration_seconds, 2),
                "duration_formatted": self._format_duration(route_result.duration_seconds),
                "total_fuel_cost": round(total_fuel_cost, 2),
                "total_gallons": round(total_gallons, 3),
                "fuel_stops_count": len(fuel_stops),
                "average_price": round(total_fuel_cost / total_gallons, 3) if total_gallons > 0 else 0
            },
            "fuel_stops": formatted_stops,
            "route": {
                "polyline": route_result.encoded_polyline,
                "coordinates": [[lon, lat] for lon, lat in route_result.coordinates_lonlat]
            }
        }