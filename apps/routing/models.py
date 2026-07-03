"""
Database models for the Spotter AI routing application.
"""

from django.db import models


class FuelStation(models.Model):
    """
    Represents a truck stop/fuel station where a vehicle can refuel.
    """

    opis_id = models.CharField(
        max_length=20,
        unique=True,
        help_text="OPIS Truckstop ID from the source data.",
    )
    truckstop_name = models.CharField(
        max_length=255,
        help_text="Name of the truck stop.",
    )
    address = models.CharField(
        max_length=255,
        help_text="Street address of the truck stop.",
    )
    city = models.CharField(
        max_length=100,
        db_index=True,
        help_text="City where the truck stop is located.",
    )
    state = models.CharField(
        max_length=2,
        db_index=True,
        help_text="Two-letter state code.",
    )
    retail_price = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        help_text="Retail price per gallon of fuel.",
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Geocoded latitude coordinate.",
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Geocoded longitude coordinate.",
    )

    class Meta:
        indexes = [
            models.Index(fields=["city", "state"]),
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["retail_price"]),
        ]
        ordering = ["state", "city", "truckstop_name"]

    def __str__(self) -> str:
        return f"{self.truckstop_name} ({self.city}, {self.state}) - ${self.retail_price}"
