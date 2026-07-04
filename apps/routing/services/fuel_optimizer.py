"""
Fuel optimization using a greedy minimum-cost algorithm.
"""

from dataclasses import dataclass
from typing import List
import logging

from apps.routing.models import FuelStation
from apps.routing.services.constants import FUEL_EFFICIENCY_MPG, MAX_FUEL_GALLONS
from apps.routing.services.exceptions import FuelOptimizationError
from apps.routing.services.station_locator import RouteStation

logger = logging.getLogger(__name__)


@dataclass
class FuelStop:
    """Represents a planned stop to refuel."""
    station: FuelStation
    gallons_purchased: float
    cost: float


class FuelOptimizer:
    """Calculates the minimum-cost refueling strategy for a route."""

    def __init__(
        self,
        mpg: float = FUEL_EFFICIENCY_MPG,
        max_gallons: float = MAX_FUEL_GALLONS
    ) -> None:
        self.mpg = mpg
        self.max_gallons = max_gallons
        self.max_range_miles = self.mpg * self.max_gallons

    def _can_reach_destination(
        self, 
        current_position: float, 
        current_fuel: float, 
        total_distance: float
    ) -> bool:
        """Check if we can reach destination with current fuel."""
        remaining_distance = total_distance - current_position
        return remaining_distance <= (current_fuel * self.mpg) + 0.1

    def _get_current_station(self, position: float, stations: List[RouteStation]) -> RouteStation:
        """Find the station at the current position."""
        for s in stations:
            if abs(s.distance_along_route_miles - position) < 0.5:
                return s
        return None

    def _get_unique_stations(self, stations: List[RouteStation]) -> List[RouteStation]:
        """Remove duplicate stations at same distance, keeping cheapest."""
        unique = {}
        for station in stations:
            dist_key = round(station.distance_along_route_miles, 1)
            if dist_key not in unique:
                unique[dist_key] = station
            else:
                if station.station.retail_price < unique[dist_key].station.retail_price:
                    unique[dist_key] = station
        result = list(unique.values())
        result.sort(key=lambda s: s.distance_along_route_miles)
        return result

    def optimize(
        self, 
        total_route_distance_miles: float, 
        route_stations: List[RouteStation]
    ) -> List[FuelStop]:
        """
        Applies a greedy algorithm to minimize fuel costs.
        
        Returns:
            List of FuelStop objects.
        """
        # If we can reach the destination without stopping
        if total_route_distance_miles <= self.max_range_miles:
            logger.info(f"Route {total_route_distance_miles:.1f} miles within range, no stops needed")
            return []

        # Sort and deduplicate stations
        stations = self._get_unique_stations(route_stations)

        if not stations:
            raise FuelOptimizationError(
                "No fuel stations were found along the calculated route."
            )

        # Remove stations at or beyond destination
        stations = [
            s for s in stations 
            if s.distance_along_route_miles < total_route_distance_miles - 0.5
        ]
        
        if not stations:
            if total_route_distance_miles <= self.max_range_miles:
                return []
            raise FuelOptimizationError(
                f"No stations found before destination at mile {total_route_distance_miles:.1f}"
            )

        logger.info(f"Found {len(stations)} valid stations before destination")
        
        if stations:
            logger.info(f"First station at mile {stations[0].distance_along_route_miles:.1f}")
            logger.info(f"Last station at mile {stations[-1].distance_along_route_miles:.1f}")

        current_fuel_gallons = self.max_gallons
        current_position_miles = 0.0
        planned_stops: List[FuelStop] = []
        visited_indices = set()
        
        iteration = 0
        while iteration < 100:
            iteration += 1
            
            # Check if we can reach destination
            if self._can_reach_destination(
                current_position_miles, 
                current_fuel_gallons, 
                total_route_distance_miles
            ):
                logger.info(f"Can reach destination from mile {current_position_miles:.1f}")
                break

            if current_position_miles >= total_route_distance_miles - 0.5:
                break

            # Find stations ahead
            stations_ahead = []
            for i, s in enumerate(stations):
                if i in visited_indices:
                    continue
                if s.distance_along_route_miles > current_position_miles + 0.5:
                    if s.distance_along_route_miles < total_route_distance_miles - 0.5:
                        stations_ahead.append((i, s))
            
            if not stations_ahead:
                if self._can_reach_destination(
                    current_position_miles, 
                    current_fuel_gallons, 
                    total_route_distance_miles
                ):
                    break
                remaining = total_route_distance_miles - current_position_miles
                if remaining <= self.max_range_miles:
                    break
                raise FuelOptimizationError(
                    f"No stations ahead from mile {current_position_miles:.1f}. "
                    f"Remaining: {remaining:.1f} miles, "
                    f"Fuel range: {current_fuel_gallons * self.mpg:.1f} miles."
                )

            # Find reachable stations
            max_reachable = current_position_miles + (current_fuel_gallons * self.mpg)
            reachable_stations = []
            for idx, s in stations_ahead:
                if s.distance_along_route_miles <= max_reachable + 0.5:
                    reachable_stations.append((idx, s))

            # CRITICAL FIX: If no reachable stations, we need to fill up more
            if not reachable_stations:
                # Check if we can reach destination first
                if self._can_reach_destination(
                    current_position_miles, 
                    current_fuel_gallons, 
                    total_route_distance_miles
                ):
                    break
                
                # If we're at a station, fill up completely
                current_station = self._get_current_station(current_position_miles, stations)
                if current_station:
                    fuel_to_buy = self.max_gallons - current_fuel_gallons
                    if fuel_to_buy > 0.001:
                        planned_stops.append(
                            FuelStop(
                                station=current_station.station,
                                gallons_purchased=round(fuel_to_buy, 3),
                                cost=round(fuel_to_buy * float(current_station.station.retail_price), 2)
                            )
                        )
                        current_fuel_gallons = self.max_gallons
                        logger.info(f"Filled up {fuel_to_buy:.2f} gal at {current_station.station.city}")
                    
                    # Recalculate reachable stations after filling up
                    max_reachable = current_position_miles + (current_fuel_gallons * self.mpg)
                    reachable_stations = []
                    for idx, s in stations_ahead:
                        if s.distance_along_route_miles <= max_reachable + 0.5:
                            reachable_stations.append((idx, s))
                    
                    # If still no reachable stations, find the closest one
                    if not reachable_stations:
                        next_station = stations_ahead[0][1]
                        distance_to_next = next_station.distance_along_route_miles - current_position_miles
                        if distance_to_next <= self.max_range_miles:
                            # We can reach it with a full tank
                            reachable_stations = [(stations_ahead[0][0], stations_ahead[0][1])]
                        else:
                            raise FuelOptimizationError(
                                f"Cannot reach next station at mile {next_station.distance_along_route_miles:.1f} "
                                f"from mile {current_position_miles:.1f}. "
                                f"Distance: {distance_to_next:.1f} miles, "
                                f"Max range: {self.max_range_miles:.1f} miles."
                            )
                else:
                    # Not at a station, find next station
                    next_station = stations_ahead[0][1]
                    distance_to_next = next_station.distance_along_route_miles - current_position_miles
                    if distance_to_next <= self.max_range_miles:
                        # We can reach it with current fuel? No, but with full tank yes
                        # But we're not at a station, so we can't fill up
                        raise FuelOptimizationError(
                            f"Cannot reach next station at mile {next_station.distance_along_route_miles:.1f} "
                            f"from mile {current_position_miles:.1f}. "
                            f"Distance: {distance_to_next:.1f} miles, "
                            f"Fuel range: {current_fuel_gallons * self.mpg:.1f} miles."
                        )

            # At origin - pick cheapest reachable
            if current_position_miles == 0:
                best_idx, best_station = min(reachable_stations, key=lambda x: float(x[1].station.retail_price))
                visited_indices.add(best_idx)
                
                distance_to_next = best_station.distance_along_route_miles - current_position_miles
                fuel_used = distance_to_next / self.mpg
                current_fuel_gallons -= fuel_used
                current_position_miles = best_station.distance_along_route_miles
                logger.info(f"First stop at {best_station.station.city} ({best_station.station.state})")
                continue

            # At a station
            current_station = self._get_current_station(current_position_miles, stations)
            if not current_station:
                if self._can_reach_destination(
                    current_position_miles, 
                    current_fuel_gallons, 
                    total_route_distance_miles
                ):
                    break
                # Find closest station
                for s in stations:
                    if s.distance_along_route_miles < current_position_miles + 1.0:
                        current_station = s
                        break
                if not current_station:
                    raise FuelOptimizationError(f"Could not find station at mile {current_position_miles:.1f}")
            
            current_price = float(current_station.station.retail_price)

            # Look for cheaper station
            cheaper_stations = [
                (idx, s) for idx, s in reachable_stations 
                if float(s.station.retail_price) < current_price
                and s.distance_along_route_miles > current_position_miles + 0.5
            ]
            
            if cheaper_stations:
                # Buy just enough to reach cheaper station
                best_idx, next_station = min(cheaper_stations, key=lambda x: float(x[1].station.retail_price))
                visited_indices.add(best_idx)
                
                distance_to_next = next_station.distance_along_route_miles - current_position_miles
                fuel_needed = distance_to_next / self.mpg
                fuel_to_buy = max(0.0, fuel_needed - current_fuel_gallons)
                
                if fuel_to_buy > 0.001:
                    planned_stops.append(
                        FuelStop(
                            station=current_station.station,
                            gallons_purchased=round(fuel_to_buy, 3),
                            cost=round(fuel_to_buy * current_price, 2)
                        )
                    )
                    current_fuel_gallons += fuel_to_buy
                    logger.info(f"Buying {fuel_to_buy:.2f} gal @ ${current_price:.3f} at {current_station.station.city}")
                
                fuel_used = distance_to_next / self.mpg
                current_fuel_gallons -= fuel_used
                current_position_miles = next_station.distance_along_route_miles
                logger.info(f"Traveling to cheaper station at {next_station.station.city}")
                
            else:
                # No cheaper station - fill up completely
                fuel_to_buy = self.max_gallons - current_fuel_gallons
                
                if fuel_to_buy > 0.001:
                    planned_stops.append(
                        FuelStop(
                            station=current_station.station,
                            gallons_purchased=round(fuel_to_buy, 3),
                            cost=round(fuel_to_buy * current_price, 2)
                        )
                    )
                    current_fuel_gallons = self.max_gallons
                    logger.info(f"Filling up {fuel_to_buy:.2f} gal @ ${current_price:.3f} at {current_station.station.city}")
                
                if self._can_reach_destination(
                    current_position_miles, 
                    current_fuel_gallons, 
                    total_route_distance_miles
                ):
                    break
                
                # Pick cheapest reachable station
                def sort_key(x):
                    return (float(x[1].station.retail_price), -x[1].distance_along_route_miles)
                
                best_idx, next_station = min(reachable_stations, key=sort_key)
                visited_indices.add(best_idx)
                
                distance_to_next = next_station.distance_along_route_miles - current_position_miles
                fuel_used = distance_to_next / self.mpg
                current_fuel_gallons -= fuel_used
                current_position_miles = next_station.distance_along_route_miles
                logger.info(f"Traveling to {next_station.station.city} (${next_station.station.retail_price})")

        # Filter out stops with 0 gallons
        planned_stops = [s for s in planned_stops if s.gallons_purchased > 0.001]
        
        total_cost = sum(s.cost for s in planned_stops)
        logger.info(f"Optimized to {len(planned_stops)} fuel stops with total cost: ${total_cost:.2f}")
        for i, stop in enumerate(planned_stops, 1):
            logger.info(f"Stop {i}: {stop.station.city}, {stop.station.state} - "
                       f"{stop.gallons_purchased:.2f} gal @ ${stop.station.retail_price} = ${stop.cost:.2f}")
        
        return planned_stops
