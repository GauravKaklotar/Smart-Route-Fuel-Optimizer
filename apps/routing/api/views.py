"""
API views for the routing application.
"""

import logging
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.routing.api.serializers import RouteRequestSerializer, RouteResponseSerializer
from apps.routing.services.cache_service import CacheService
from apps.routing.services.fuel_optimizer import FuelOptimizer
from apps.routing.services.geocoder import GeocodingService
from apps.routing.services.response_builder import ResponseBuilder
from apps.routing.services.routing_service import RoutingService
from apps.routing.services.station_locator import StationLocator
from apps.routing.services.exceptions import GeocodingError, RoutingError, FuelOptimizationError

logger = logging.getLogger(__name__)


class RouteView(APIView):
    """
    API endpoint to calculate an optimal driving route and fuel stops.
    """

    @extend_schema(
        request=RouteRequestSerializer,
        responses={200: RouteResponseSerializer},
        summary="Calculate optimal fuel route",
        description="Calculates a driving route between two USA locations and finds the optimal fuel stops to minimize total fuel cost.",
    )
    def post(self, request, *args, **kwargs):
        try:
            # 1. Validate request
            serializer = RouteRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            start_loc = serializer.validated_data["start"]
            dest_loc = serializer.validated_data["destination"]

            # 2. Check cache
            cache_service = CacheService()
            cached_response = cache_service.get_route(start_loc, dest_loc)
            if cached_response:
                return Response(cached_response, status=status.HTTP_200_OK)

            # 3. Geocode origin and destination
            geocoder = GeocodingService()
            start_coords = geocoder.geocode(start_loc)
            dest_coords = geocoder.geocode(dest_loc)

            # 4. Get route from ORS
            router = RoutingService()
            route_result = router.get_route(start_coords, dest_coords)

            # 5. Find stations near route
            locator = StationLocator()
            route_stations = locator.find_stations_near_route(
                route_result.coordinates_lonlat
            )

            logger.info(f"Total stations found near route: {len(route_stations)}")
            if route_stations:
                logger.info(f"First station: {route_stations[0].station.city}, {route_stations[0].station.state} at mile {route_stations[0].distance_along_route_miles:.1f}")
                logger.info(f"Last station: {route_stations[-1].station.city}, {route_stations[-1].station.state} at mile {route_stations[-1].distance_along_route_miles:.1f}")
                
                # Log gaps
                gaps = []
                prev_dist = 0
                for s in route_stations[:10]:  # Check first 10
                    gap = s.distance_along_route_miles - prev_dist
                    gaps.append(gap)
                    prev_dist = s.distance_along_route_miles
                logger.info(f"First 10 gaps: {gaps}")

            # 6. Optimize fuel stops
            optimizer = FuelOptimizer()
            fuel_stops = optimizer.optimize(
                total_route_distance_miles=route_result.distance_miles,
                route_stations=route_stations,
            )

            # 7. Build response
            builder = ResponseBuilder()
            response_data = builder.build(route_result, fuel_stops)

            # 8. Cache and return
            cache_service.set_route(start_loc, dest_loc, response_data)
            return Response(response_data, status=status.HTTP_200_OK)
            
        except GeocodingError as e:
            logger.error(f"Geocoding error: {str(e)}")
            return Response(
                {"error": {"type": "geocoding_error", "message": str(e)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except RoutingError as e:
            logger.error(f"Routing error: {str(e)}")
            return Response(
                {"error": {"type": "routing_error", "message": str(e)}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except FuelOptimizationError as e:
            logger.error(f"Fuel optimization error: {str(e)}")
            return Response(
                {"error": {"type": "fuel_optimization_error", "message": str(e)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return Response(
                {"error": {"type": "internal_error", "message": "An unexpected error occurred"}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


