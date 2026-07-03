"""
Tests for API serializers.
"""

from apps.routing.api.serializers import RouteRequestSerializer


def test_route_request_serializer_valid():
    data = {"start": "Dallas, TX", "destination": "Chicago, IL"}
    serializer = RouteRequestSerializer(data=data)
    assert serializer.is_valid()
    assert serializer.validated_data["start"] == "dallas, tx"


def test_route_request_serializer_missing_fields():
    serializer = RouteRequestSerializer(data={"start": "Dallas, TX"})
    assert not serializer.is_valid()
    assert "destination" in serializer.errors


def test_route_request_serializer_same_locations():
    data = {"start": "Dallas, TX", "destination": "  Dallas, TX "}
    serializer = RouteRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "non_field_errors" in serializer.errors
    assert "different" in str(serializer.errors["non_field_errors"][0])


def test_route_request_serializer_empty_strings():
    data = {"start": " ", "destination": "Chicago, IL"}
    serializer = RouteRequestSerializer(data=data)
    assert not serializer.is_valid()
    assert "start" in serializer.errors
