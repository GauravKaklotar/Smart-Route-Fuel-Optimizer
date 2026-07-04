"""
Management command to add test fuel station data for testing.
"""

from django.core.management.base import BaseCommand
from apps.routing.models import FuelStation


class Command(BaseCommand):
    help = 'Add test fuel station data along major highways'

    def handle(self, *args, **options):
        self.stdout.write('Adding test fuel station data...')
        
        # I-10 Corridor: Phoenix to Dallas
        i10_stations = [
            # AZ - Phoenix area
            ("BUCKEYE", "AZ", 33.3703, -112.5838, 3.45, "Buckeye Truck Stop"),
            ("GOODYEAR", "AZ", 33.4322, -112.3582, 3.38, "Goodyear Fuel Center"),
            ("TOLLESON", "AZ", 33.4500, -112.2594, 3.52, "Tolleson Truck Plaza"),
            ("MESA", "AZ", 33.4152, -111.8315, 3.30, "Mesa Travel Center"),
            
            # AZ - I-10 East
            ("ELOY", "AZ", 32.7562, -111.5545, 3.14, "Eloy Truck Stop"),
            ("PICACHO", "AZ", 32.7167, -111.5000, 3.25, "Picacho Peak Fuel"),
            ("TUCSON", "AZ", 32.2226, -110.9747, 3.06, "Tucson Travel Plaza"),
            ("BENSON", "AZ", 31.9679, -110.2945, 3.22, "Benson Truck Stop"),
            ("WILLCOX", "AZ", 32.2528, -109.8325, 3.28, "Willcox Travel Center"),
            ("SAN SIMON", "AZ", 32.2679, -109.2276, 2.96, "San Simon Fuel Stop"),
            
            # NM
            ("LORDSBURG", "NM", 32.3504, -108.7087, 3.44, "Lordsburg Truck Stop"),
            ("DEMING", "NM", 32.2687, -107.7586, 2.90, "Deming Travel Plaza"),
            ("LAS CRUCES", "NM", 32.3199, -106.7637, 3.14, "Las Cruces Fuel Center"),
            
            # TX - El Paso to Dallas
            ("EL PASO", "TX", 31.7619, -106.4850, 2.70, "El Paso Truck Stop"),
            ("SIERRA BLANCA", "TX", 31.1749, -105.3570, 3.05, "Sierra Blanca Fuel"),
            ("VAN HORN", "TX", 31.0399, -104.8308, 3.10, "Van Horn Travel Center"),
            ("PECOS", "TX", 31.4229, -103.4930, 2.99, "Pecos Truck Stop"),
            ("KERMIT", "TX", 31.8530, -103.0927, 3.04, "Kermit Fuel Stop"),
            ("MONAHANS", "TX", 31.5943, -102.8927, 2.86, "Monahans Travel Plaza"),
            ("ODESSA", "TX", 31.8457, -102.3676, 2.95, "Odessa Truck Center"),
            ("MIDLAND", "TX", 31.9973, -102.0779, 2.85, "Midland Travel Stop"),
            ("STANTON", "TX", 32.1293, -101.7880, 3.02, "Stanton Fuel"),
            ("BIG SPRING", "TX", 32.2504, -101.4787, 3.65, "Big Spring Truck Stop"),
            ("COLORADO CITY", "TX", 32.3881, -100.8646, 2.90, "Colorado City Fuel"),
            ("SNYDER", "TX", 32.7179, -100.9178, 2.97, "Snyder Travel Center"),
            ("SWEETWATER", "TX", 32.4709, -100.4054, 2.85, "Sweetwater Truck Stop"),
            ("ABILENE", "TX", 32.4487, -99.7331, 2.77, "Abilene Fuel Center"),
            ("CISCO", "TX", 32.3882, -98.9786, 2.93, "Cisco Truck Stop"),
            ("EASTLAND", "TX", 32.4015, -98.8176, 2.95, "Eastland Travel Plaza"),
            ("WEATHERFORD", "TX", 32.7593, -97.7970, 2.92, "Weatherford Truck Stop"),
            ("FORT WORTH", "TX", 32.7555, -97.3308, 2.70, "Fort Worth Travel Center"),
        ]
        
        added_count = 0
        skipped_count = 0
        
        for city, state, lat, lon, price, name in i10_stations:
            # Check if station already exists
            existing = FuelStation.objects.filter(
                city__iexact=city,
                state=state,
                latitude__isnull=False
            ).first()
            
            if not existing:
                FuelStation.objects.create(
                    opis_id=f"I10_{city[:3]}_{state}_{added_count+1}",
                    truckstop_name=name,
                    address="I-10 Frontage Road",
                    city=city,
                    state=state,
                    retail_price=price,
                    latitude=lat,
                    longitude=lon
                )
                added_count += 1
                self.stdout.write(f"✓ Added: {city}, {state} - ${price}")
            else:
                skipped_count += 1
                self.stdout.write(f"  Skipped: {city}, {state} (already exists)")
        
        total_geocoded = FuelStation.objects.filter(latitude__isnull=False).count()
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Done! Added {added_count} stations, skipped {skipped_count}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Total geocoded stations: {total_geocoded}'
        ))