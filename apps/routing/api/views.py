"""
API views for the routing application.
"""

import logging
from django.db.models import Q, Avg, Min, Max, Count
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.routing.api.serializers import (
    RouteRequestSerializer, 
    RouteResponseSerializer,
    SearchSerializer,
    PriceFilterSerializer
)
from apps.routing.services.cache_service import CacheService
from apps.routing.services.fuel_optimizer import FuelOptimizer
from apps.routing.services.geocoder import GeocodingService
from apps.routing.services.response_builder import ResponseBuilder
from apps.routing.services.routing_service import RoutingService
from apps.routing.services.station_locator import StationLocator
from apps.routing.models import FuelStation
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


class HealthCheckView(APIView):
    """
    Health check endpoint to verify all services are running.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Health Check",
        description="Check if the API and its dependencies are healthy.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "healthy"},
                    "version": {"type": "string", "example": "1.0.0"},
                    "services": {
                        "type": "object",
                        "properties": {
                            "database": {"type": "string", "example": "healthy"},
                            "redis": {"type": "string", "example": "healthy"},
                            "ors_api": {"type": "string", "example": "healthy"}
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        health_status = {
            "status": "healthy",
            "version": "1.0.0",
            "services": {}
        }

        # Check database
        try:
            FuelStation.objects.exists()
            health_status["services"]["database"] = "healthy"
        except Exception as e:
            health_status["services"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"

        # Check Redis cache
        try:
            cache.set("health_check", "ok", 5)
            cache.get("health_check")
            health_status["services"]["redis"] = "healthy"
        except Exception as e:
            health_status["services"]["redis"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"

        # Check ORS API (lightweight check)
        try:
            from django.conf import settings
            import requests
            ors_url = f"{settings.ORS_BASE_URL}/health"
            response = requests.get(ors_url, timeout=5)
            if response.status_code == 200:
                health_status["services"]["ors_api"] = "healthy"
            else:
                health_status["services"]["ors_api"] = "degraded"
        except Exception as e:
            health_status["services"]["ors_api"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"

        status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health_status, status=status_code)


class SearchLocationsView(APIView):
    """
    Search for locations to help users find start/destination.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="q", description="Search query", required=True, type=str),
            OpenApiParameter(name="limit", description="Max results", required=False, type=int),
        ],
        summary="Search Locations",
        description="Search for US cities and states to help users find locations.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "state": {"type": "string"},
                                "display": {"type": "string"},
                                "stations_count": {"type": "integer"},
                                "avg_price": {"type": "number"}
                            }
                        }
                    },
                    "total": {"type": "integer"}
                }
            }
        }
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        limit = int(request.query_params.get("limit", 10))
        
        if not query:
            return Response(
                {"error": {"message": "Search query parameter 'q' is required"}},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Search in database
        search_terms = query.split()
        q_objects = Q()
        
        for term in search_terms:
            q_objects |= Q(city__icontains=term) | Q(state__icontains=term)
        
        # Get unique city/state combinations with station data
        results = (
            FuelStation.objects
            .filter(q_objects, latitude__isnull=False)
            .values('city', 'state')
            .annotate(
                stations_count=Count('id'),
                avg_price=Avg('retail_price'),
                min_price=Min('retail_price'),
                max_price=Max('retail_price')
            )
            .order_by('-stations_count')[:limit]
        )

        formatted_results = []
        for r in results:
            formatted_results.append({
                "city": r['city'],
                "state": r['state'],
                "display": f"{r['city']}, {r['state']}",
                "stations_count": r['stations_count'],
                "avg_price": round(r['avg_price'], 3) if r['avg_price'] else None,
                "min_price": round(r['min_price'], 3) if r['min_price'] else None,
                "max_price": round(r['max_price'], 3) if r['max_price'] else None
            })

        return Response({
            "results": formatted_results,
            "total": len(formatted_results),
            "query": query
        })


class FuelPricesView(APIView):
    """
    Get fuel price statistics and search for cheapest stations.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="state", description="Filter by state (2-letter code)", required=False, type=str),
            OpenApiParameter(name="city", description="Filter by city", required=False, type=str),
            OpenApiParameter(name="limit", description="Number of results", required=False, type=int),
            OpenApiParameter(name="sort", description="Sort by price (asc/desc)", required=False, type=str),
        ],
        summary="Fuel Prices",
        description="Get fuel price statistics and find the cheapest stations.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "object",
                        "properties": {
                            "total_stations": {"type": "integer"},
                            "avg_price": {"type": "number"},
                            "min_price": {"type": "number"},
                            "max_price": {"type": "number"},
                            "cheapest_state": {"type": "string"},
                            "most_expensive_state": {"type": "string"}
                        }
                    },
                    "stations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "opis_id": {"type": "string"},
                                "name": {"type": "string"},
                                "city": {"type": "string"},
                                "state": {"type": "string"},
                                "retail_price": {"type": "number"},
                                "address": {"type": "string"},
                                "coordinates": {
                                    "type": "object",
                                    "properties": {
                                        "latitude": {"type": "number"},
                                        "longitude": {"type": "number"}
                                    }
                                }
                            }
                        }
                    },
                    "state_stats": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "state": {"type": "string"},
                                "stations": {"type": "integer"},
                                "avg_price": {"type": "number"},
                                "min_price": {"type": "number"},
                                "max_price": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        # Get filter parameters
        state = request.query_params.get("state", "").strip().upper()
        city = request.query_params.get("city", "").strip()
        limit = int(request.query_params.get("limit", 20))
        sort = request.query_params.get("sort", "asc")  # asc or desc

        # Build query
        queryset = FuelStation.objects.filter(latitude__isnull=False)
        
        if state:
            queryset = queryset.filter(state=state)
        if city:
            queryset = queryset.filter(city__icontains=city)

        # Get summary statistics
        summary = {}
        if queryset.exists():
            summary = {
                "total_stations": queryset.count(),
                "avg_price": round(queryset.aggregate(Avg('retail_price'))['retail_price__avg'] or 0, 3),
                "min_price": round(queryset.aggregate(Min('retail_price'))['retail_price__min'] or 0, 3),
                "max_price": round(queryset.aggregate(Max('retail_price'))['retail_price__max'] or 0, 3),
            }

        # Get cheapest and most expensive states
        state_stats = (
            FuelStation.objects
            .filter(latitude__isnull=False)
            .values('state')
            .annotate(
                stations=Count('id'),
                avg_price=Avg('retail_price'),
                min_price=Min('retail_price'),
                max_price=Max('retail_price')
            )
            .filter(stations__gte=10)  # Only states with at least 10 stations
            .order_by('avg_price')
        )

        if state_stats.exists():
            cheapest = state_stats.first()
            most_expensive = state_stats.last()
            summary["cheapest_state"] = cheapest['state'] if cheapest else None
            summary["cheapest_state_avg_price"] = round(cheapest['avg_price'], 3) if cheapest else None
            summary["most_expensive_state"] = most_expensive['state'] if most_expensive else None
            summary["most_expensive_state_avg_price"] = round(most_expensive['avg_price'], 3) if most_expensive else None

        # Get stations
        if sort == "asc":
            queryset = queryset.order_by('retail_price')
        else:
            queryset = queryset.order_by('-retail_price')

        stations = queryset[:limit]

        formatted_stations = []
        for station in stations:
            formatted_stations.append({
                "opis_id": station.opis_id,
                "name": station.truckstop_name,
                "city": station.city,
                "state": station.state,
                "retail_price": float(station.retail_price),
                "address": station.address,
                "coordinates": {
                    "latitude": station.latitude,
                    "longitude": station.longitude
                } if station.latitude else None
            })

        # Format state stats
        formatted_state_stats = []
        for stat in state_stats[:20]:  # Top 20 states
            formatted_state_stats.append({
                "state": stat['state'],
                "stations": stat['stations'],
                "avg_price": round(stat['avg_price'], 3),
                "min_price": round(stat['min_price'], 3),
                "max_price": round(stat['max_price'], 3)
            })

        return Response({
            "summary": summary,
            "stations": formatted_stations,
            "state_stats": formatted_state_stats,
            "filters": {
                "state": state if state else "all",
                "city": city if city else "all",
                "limit": limit,
                "sort": sort
            }
        })