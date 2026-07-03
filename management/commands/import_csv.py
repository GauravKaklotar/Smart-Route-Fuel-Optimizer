"""
Management command to import fuel stations from CSV.
"""

import logging
from typing import Any
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings

from apps.routing.models import FuelStation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Imports fuel stations from a CSV file.
    Expects headers: OPIS Truckstop ID, Truckstop Name, Address, City, State, Rack ID, Retail Price
    """

    help = "Imports fuel stations from CSV file located at data/fuel_stations.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=str(settings.DATA_DIR / "fuel_stations.csv"),
            help="Path to the CSV file",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        file_path = Path(options["file"])

        if not file_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write(f"Reading CSV from {file_path}...")

        try:
            # Read CSV using pandas, ensuring OPIS ID is read as string
            df = pd.read_csv(
                file_path,
                dtype={"OPIS Truckstop ID": str},
            )
            # Clean column names (strip whitespace)
            df.columns = df.columns.str.strip()
            
            # Require essential columns
            required_columns = [
                "OPIS Truckstop ID",
                "Truckstop Name",
                "Address",
                "City",
                "State",
                "Retail Price",
            ]
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                self.stderr.write(self.style.ERROR(f"Missing columns: {missing_cols}"))
                return

            # Clean data
            df = df.dropna(subset=required_columns)
            # Ensure price is numeric
            df["Retail Price"] = pd.to_numeric(df["Retail Price"], errors="coerce")
            df = df.dropna(subset=["Retail Price"])
            # Filter out invalid prices (<= 0)
            df = df[df["Retail Price"] > 0]
            
            # Drop duplicate OPIS IDs in the CSV just in case
            df = df.drop_duplicates(subset=["OPIS Truckstop ID"], keep="last")

            stations_to_create = []
            
            self.stdout.write("Processing rows...")
            for _, row in df.iterrows():
                stations_to_create.append(
                    FuelStation(
                        opis_id=str(row["OPIS Truckstop ID"]).strip(),
                        truckstop_name=str(row["Truckstop Name"]).strip(),
                        address=str(row["Address"]).strip(),
                        city=str(row["City"]).strip(),
                        state=str(row["State"]).strip(),
                        retail_price=row["Retail Price"],
                    )
                )

            # Bulk create ignoring conflicts (if opis_id already exists)
            self.stdout.write("Saving to database...")
            FuelStation.objects.bulk_create(
                stations_to_create,
                batch_size=1000,
                ignore_conflicts=True
            )

            self.stdout.write(self.style.SUCCESS(f"Successfully processed {len(stations_to_create)} valid stations."))
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error during import: {e}"))
            logger.exception("CSV import failed")
