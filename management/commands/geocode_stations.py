"""
Management command to geocode fuel stations by city/state using OpenRouteService.
"""

import time
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.routing.models import FuelStation
from apps.routing.services.geocoder import GeocodingService
from apps.routing.services.exceptions import GeocodingError


class Command(BaseCommand):
    """
    Geocodes unique (city, state) pairs that have NULL coordinates,
    then updates all matching FuelStations.
    Respects ORS rate limits.
    """

    help = "Geocodes fuel stations by unique city/state combinations"

    def handle(self, *args: Any, **options: Any) -> None:
        # Find unique city/state combinations that need geocoding
        # Ordered by the number of stations in that city (most first)
        locations = (
            FuelStation.objects.filter(latitude__isnull=True)
            .values("city", "state")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        total_locations = locations.count()
        if total_locations == 0:
            self.stdout.write(self.style.SUCCESS("No stations need geocoding."))
            return

        self.stdout.write(f"Found {total_locations} unique city/state pairs to geocode.")
        
        geocoder = GeocodingService()
        
        success_count = 0
        error_count = 0
        stations_updated = 0
        
        for index, loc in enumerate(locations, 1):
            city = loc["city"]
            state = loc["state"]
            station_count = loc["count"]
            query_str = f"{city}, {state}, USA"
            
            self.stdout.write(f"[{index}/{total_locations}] Geocoding: {query_str} ({station_count} stations)")
            
            try:
                # Get coordinates
                lon, lat = geocoder.geocode(query_str)
                
                # Update all stations with this city/state
                updated = FuelStation.objects.filter(
                    city=city, 
                    state=state,
                    latitude__isnull=True
                ).update(
                    latitude=lat,
                    longitude=lon
                )
                
                stations_updated += updated
                success_count += 1
                
            except GeocodingError as e:
                self.stderr.write(self.style.WARNING(f"  Warning: Geocoding failed for {query_str}: {e}"))
                error_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  Error: {e}"))
                error_count += 1
                
            # Rate limiting for ORS (Standard tier allows ~40 req/min)
            # Sleep 1.5 seconds between requests (40/min)
            time.sleep(1.5)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nGeocoding complete!\n"
                f"Successfully geocoded: {success_count} locations\n"
                f"Failed: {error_count} locations\n"
                f"Total stations updated: {stations_updated}"
            )
        )
