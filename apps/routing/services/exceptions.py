"""
Custom exception hierarchy for the Spotter AI application.
"""

class SpotterAPIError(Exception):
    """Base exception for all Spotter API errors."""
    pass


class GeocodingError(SpotterAPIError):
    """Raised when geocoding a location fails."""
    pass


class RoutingError(SpotterAPIError):
    """Raised when calculating a route fails."""
    pass


class FuelOptimizationError(SpotterAPIError):
    """Raised when the fuel optimization algorithm encounters an error."""
    pass
