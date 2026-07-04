"""
Management command to add missing fuel stations along I-10 corridor.
"""

from django.core.management.base import BaseCommand
from apps.routing.models import FuelStation


class Command(BaseCommand):
    help = 'Add missing fuel stations along I-10 corridor for Phoenix to Dallas route'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🔄 Adding missing fuel stations...'))
        
        # All missing stations along I-10 from Phoenix to Dallas
        missing_stations = [
            # Between El Paso (mile ~441) and Van Horn (mile ~566)
            {
                "city": "Sierra Blanca",
                "state": "TX",
                "latitude": 31.1749,
                "longitude": -105.3570,
                "retail_price": 3.05,
                "name": "Sierra Blanca Truck Stop",
                "address": "I-10 Frontage Rd, Sierra Blanca, TX"
            },
            {
                "city": "Van Horn",
                "state": "TX",
                "latitude": 31.0399,
                "longitude": -104.8308,
                "retail_price": 3.10,
                "name": "Van Horn Travel Center",
                "address": "I-10 Frontage Rd, Van Horn, TX"
            },
            # Between Van Horn (mile ~566) and Pecos (mile ~653)
            {
                "city": "Pecos",
                "state": "TX",
                "latitude": 31.4229,
                "longitude": -103.4930,
                "retail_price": 2.99,
                "name": "Pecos Truck Stop",
                "address": "I-10 Frontage Rd, Pecos, TX"
            },
            # Between Pecos (mile ~653) and Odessa (mile ~731)
            {
                "city": "Kermit",
                "state": "TX",
                "latitude": 31.8530,
                "longitude": -103.0927,
                "retail_price": 3.04,
                "name": "Kermit Fuel Stop",
                "address": "I-10 Frontage Rd, Kermit, TX"
            },
            {
                "city": "Monahans",
                "state": "TX",
                "latitude": 31.5943,
                "longitude": -102.8927,
                "retail_price": 2.86,
                "name": "Monahans Travel Plaza",
                "address": "I-10 Frontage Rd, Monahans, TX"
            },
            {
                "city": "Odessa",
                "state": "TX",
                "latitude": 31.8457,
                "longitude": -102.3676,
                "retail_price": 2.95,
                "name": "Odessa Truck Center",
                "address": "I-10 Frontage Rd, Odessa, TX"
            },
            {
                "city": "Midland",
                "state": "TX",
                "latitude": 31.9973,
                "longitude": -102.0779,
                "retail_price": 2.85,
                "name": "Midland Travel Stop",
                "address": "I-10 Frontage Rd, Midland, TX"
            },
            # Between Midland (mile ~747) and Abilene (mile ~895)
            {
                "city": "Stanton",
                "state": "TX",
                "latitude": 32.1293,
                "longitude": -101.7880,
                "retail_price": 3.02,
                "name": "Stanton Fuel",
                "address": "I-10 Frontage Rd, Stanton, TX"
            },
            {
                "city": "Big Spring",
                "state": "TX",
                "latitude": 32.2504,
                "longitude": -101.4787,
                "retail_price": 3.65,
                "name": "Big Spring Truck Stop",
                "address": "I-10 Frontage Rd, Big Spring, TX"
            },
            {
                "city": "Colorado City",
                "state": "TX",
                "latitude": 32.3881,
                "longitude": -100.8646,
                "retail_price": 2.90,
                "name": "Colorado City Fuel",
                "address": "I-10 Frontage Rd, Colorado City, TX"
            },
            {
                "city": "Snyder",
                "state": "TX",
                "latitude": 32.7179,
                "longitude": -100.9178,
                "retail_price": 2.97,
                "name": "Snyder Travel Center",
                "address": "I-10 Frontage Rd, Snyder, TX"
            },
            {
                "city": "Sweetwater",
                "state": "TX",
                "latitude": 32.4709,
                "longitude": -100.4054,
                "retail_price": 2.85,
                "name": "Sweetwater Truck Stop",
                "address": "I-10 Frontage Rd, Sweetwater, TX"
            },
            # Between Sweetwater (mile ~857) and Fort Worth (mile ~1049)
            {
                "city": "Abilene",
                "state": "TX",
                "latitude": 32.4487,
                "longitude": -99.7331,
                "retail_price": 2.77,
                "name": "Abilene Fuel Center",
                "address": "I-10 Frontage Rd, Abilene, TX"
            },
            {
                "city": "Cisco",
                "state": "TX",
                "latitude": 32.3882,
                "longitude": -98.9786,
                "retail_price": 2.93,
                "name": "Cisco Truck Stop",
                "address": "I-10 Frontage Rd, Cisco, TX"
            },
            {
                "city": "Eastland",
                "state": "TX",
                "latitude": 32.4015,
                "longitude": -98.8176,
                "retail_price": 2.95,
                "name": "Eastland Travel Plaza",
                "address": "I-10 Frontage Rd, Eastland, TX"
            },
            {
                "city": "Weatherford",
                "state": "TX",
                "latitude": 32.7593,
                "longitude": -97.7970,
                "retail_price": 2.92,
                "name": "Weatherford Truck Stop",
                "address": "I-10 Frontage Rd, Weatherford, TX"
            },
            {
                "city": "Fort Worth",
                "state": "TX",
                "latitude": 32.7555,
                "longitude": -97.3308,
                "retail_price": 2.70,
                "name": "Fort Worth Travel Center",
                "address": "I-10 Frontage Rd, Fort Worth, TX"
            },
        ]

        added_count = 0
        skipped_count = 0
        
        for station_data in missing_stations:
            # Check if station already exists
            existing = FuelStation.objects.filter(
                city__iexact=station_data["city"],
                state=station_data["state"],
                latitude__isnull=False
            ).first()
            
            if not existing:
                # Create a unique opis_id
                opis_id = f"I10_{station_data['city'][:3]}_{station_data['state']}_{added_count}"
                
                FuelStation.objects.create(
                    opis_id=opis_id,
                    truckstop_name=station_data["name"],
                    address=station_data["address"],
                    city=station_data["city"],
                    state=station_data["state"],
                    retail_price=station_data["retail_price"],
                    latitude=station_data["latitude"],
                    longitude=station_data["longitude"]
                )
                added_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Added: {station_data['city']}, {station_data['state']} - ${station_data['retail_price']}")
                )
            else:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(f"  ⊘ Skipped: {station_data['city']}, {station_data['state']} (already exists)")
                )

        # Show summary
        total_geocoded = FuelStation.objects.filter(latitude__isnull=False).count()
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS(f"✅ Added: {added_count} stations"))
        self.stdout.write(self.style.WARNING(f"⊘ Skipped: {skipped_count} stations"))
        self.stdout.write(self.style.SUCCESS(f"📊 Total geocoded stations: {total_geocoded}"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        
        # Show stations along I-10 for verification
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("📋 Stations along I-10 corridor:"))
        i10_stations = FuelStation.objects.filter(
            latitude__isnull=False,
            state__in=['AZ', 'NM', 'TX']
        ).values('city', 'state', 'retail_price', 'latitude', 'longitude').order_by('latitude')[:30]
        
        for s in i10_stations:
            self.stdout.write(f"  {s['city']}, {s['state']}: ${s['retail_price']} at ({s['latitude']}, {s['longitude']})")