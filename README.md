# Spotter AI — Fuel Route Optimization API

A production-ready REST API built with Django 5.2 LTS that computes optimal driving routes with cost-minimized fuel stops across the USA.

## Architecture

The system is built on a clean architecture model with a "thin views, fat services" philosophy. 

```mermaid
flowchart TD
    Client[Client] --> View[RouteView (API)]
    
    subgraph Services
        View --> Orchestrator[Route Orchestrator]
        Orchestrator <--> Cache[CacheService]
        Orchestrator --> Geocoder[GeocodingService]
        Orchestrator --> Router[RoutingService]
        Orchestrator --> Locator[StationLocator]
        Orchestrator --> Optimizer[FuelOptimizer]
        Orchestrator --> Builder[ResponseBuilder]
    end

    Geocoder -- REST API --> ORS_Geo[OpenRouteService Geocoding]
    Router -- REST API --> ORS_Dir[OpenRouteService Directions]
    
    Locator -- BallTree Spatial Search --> DB[(PostgreSQL)]
```

## Engineering Trade-offs & Decisions

### 1. City-Level Geocoding Strategy
**Challenge**: The provided CSV contains over 10,000 truck stops. Many addresses are listed as highway intersections (e.g. `"I-44, EXIT 283 & US-69"`). Standard geocoders struggle to precisely locate these rural highway exits. Additionally, calling an external geocoding API 10,000+ times is slow and exhausts free-tier quotas quickly.
**Decision**: We extract unique `(City, State)` combinations from the database and geocode the city centers instead. All stations in a city share the city-center coordinates.
**Trade-off**: We sacrifice granular street-level accuracy for 100% successful geocoding, massive API quota savings, and rapid database hydration. Given our 5-mile search buffer along the highway, city-center accuracy is sufficient for highway-adjacent truck stops.

### 2. Spatial Indexing without PostGIS
**Challenge**: The assessment requires free technologies but explicitly forbids PostGIS, which is the industry standard for spatial queries.
**Decision**: We load geocoded stations into memory upon server start and build a **Scikit-learn BallTree**. We convert latitudes/longitudes to radians and use the `haversine` metric to perform ultra-fast radius queries ($\mathcal{O}(\log N)$). 
**Trade-off**: Requires memory to hold the BallTree (negligible for 10k points), but completely eliminates the need for complex database spatial extensions. We project coordinates to `EPSG:5070` (CONUS Albers) dynamically via `pyproj` to perform accurate meter-based buffering.

### 3. Fuel Optimization Algorithm
We implemented a **Greedy Minimum-Cost Refueling Algorithm**.
- **Rules**: 500-mile max range, 10 MPG (50 gallon tank).
- **Logic**: At any given stop, the algorithm looks ahead to all reachable stations (within 500 miles).
  - If a **cheaper** station is found ahead, we purchase *only the exact amount of fuel required* to reach that cheaper station.
  - If **no cheaper** station is found ahead, we fill the tank completely (up to 50 gallons) to maximize travel on the current cheap fuel, and plan our next stop at the cheapest reachable station.

---

## Installation & Setup

### Prerequisites
- Docker & Docker Compose
- OpenRouteService API Key

### 1. Environment Variables
Copy the template and add your ORS API key:
```bash
cp .env.example .env
# Edit .env and insert your ORS_API_KEY
```

### 2. Add Data
Place your CSV file containing the truck stops into the data folder:
`data/fuel_stations.csv`

### 3. Start Infrastructure
Start the application, PostgreSQL database, and Redis cache:
```bash
docker compose up -d
```
*Note: The Docker entrypoint will automatically wait for the DB to be ready, run migrations, and collect static files.*

### 4. Import & Geocode Data
Run the management commands to populate the database and fetch coordinates:
```bash
# Import the CSV (extremely fast using Pandas & bulk_create)
docker compose exec web python manage.py import_csv

# Geocode the unique cities (respects ORS rate limits, takes a few minutes)
docker compose exec web python manage.py geocode_stations
```

---

## API Documentation

### Interactive Swagger UI
Once running, the interactive Swagger documentation is available at:
👉 **`http://localhost:8000/api/docs/`**

### Calculate Route & Fuel Stops
**POST** `/api/v1/routes/`

**Request Body:**
```json
{
    "start": "Dallas, TX",
    "destination": "Chicago, IL"
}
```

**Response:**
```json
{
    "distance": 923.45,
    "duration": 50400.0,
    "total_fuel_cost": 284.50,
    "fuel_stops": [
        {
            "opis_id": "123",
            "name": "TA Travel Center",
            "location": "Oklahoma City, OK",
            "retail_price": 3.10,
            "gallons_purchased": 20.5,
            "cost": 63.55,
            "coordinates": {
                "latitude": 35.4676,
                "longitude": -97.5164
            }
        }
    ],
    "route": {
        "polyline": "gfo}Eto_xO~`@e^...",
        "coordinates": [
            [-96.7970, 32.7767],
            [-96.7971, 32.7768]
        ]
    }
}
```

---

## Future Improvements

1. **Background Tasks (Celery)**: If permitted, the CSV import and geocoding process should be moved to Celery workers rather than synchronous CLI commands.
2. **True Spatial DB**: Moving to PostGIS would allow for dynamic bounding box queries directly in the database without needing to hold a BallTree in memory, making it easier to scale across multiple gunicorn workers.
3. **Advanced Routing**: The current algorithm uses a simplified route line for spatial queries to ensure speed. We could utilize ORS Isochrones for highly accurate drive-time radius searches instead of geographic buffers.
