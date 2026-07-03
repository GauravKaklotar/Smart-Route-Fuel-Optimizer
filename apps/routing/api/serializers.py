"""
API serializers for request validation and response schema definition.
"""

from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    """Validates the incoming route request."""
    
    start = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Starting location within the USA (e.g. 'Dallas, TX')"
    )
    destination = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Destination location within the USA (e.g. 'Chicago, IL')"
    )

    def validate(self, attrs):
        start = attrs.get("start", "").strip().lower()
        destination = attrs.get("destination", "").strip().lower()

        if not start:
            raise serializers.ValidationError({"start": "Start location cannot be empty."})
        
        if not destination:
            raise serializers.ValidationError({"destination": "Destination location cannot be empty."})

        if start == destination:
            raise serializers.ValidationError(
                "Start and destination locations must be different."
            )

        return attrs


class CoordinatesSerializer(serializers.Serializer):
    """Schema for a geographic coordinate."""
    latitude = serializers.FloatField(help_text="Latitude coordinate")
    longitude = serializers.FloatField(help_text="Longitude coordinate")


class FuelStopSchemaSerializer(serializers.Serializer):
    """Schema for a fuel stop in the response (used for Swagger)."""
    opis_id = serializers.CharField(help_text="OPIS ID of the station")
    name = serializers.CharField(help_text="Name of the truck stop")
    location = serializers.CharField(help_text="City and State")
    retail_price = serializers.FloatField(help_text="Price per gallon")
    gallons_purchased = serializers.FloatField(help_text="Amount of fuel to purchase")
    cost = serializers.FloatField(help_text="Total cost of fuel at this stop")
    coordinates = CoordinatesSerializer()


class RouteGeometrySchemaSerializer(serializers.Serializer):
    """Schema for the route geometry (used for Swagger)."""
    polyline = serializers.CharField(help_text="Encoded polyline string")
    coordinates = serializers.ListField(
        child=serializers.ListField(
            child=serializers.FloatField(),
            help_text="[longitude, latitude]"
        ),
        help_text="List of coordinate pairs [lon, lat]"
    )


class RouteResponseSerializer(serializers.Serializer):
    """Schema for the complete route response (used for Swagger)."""
    distance = serializers.FloatField(help_text="Total distance in miles")
    duration = serializers.FloatField(help_text="Total duration in seconds")
    total_fuel_cost = serializers.FloatField(help_text="Total cost of all fuel stops")
    fuel_stops = FuelStopSchemaSerializer(many=True, help_text="Ordered list of fuel stops")
    route = RouteGeometrySchemaSerializer()
