"""
Fuel optimization using a greedy minimum-cost algorithm.
"""

from dataclasses import dataclass
from typing import List

from apps.routing.models import FuelStation
from apps.routing.services.constants import FUEL_EFFICIENCY_MPG, MAX_FUEL_GALLONS
from apps.routing.services.exceptions import FuelOptimizationError
from apps.routing.services.station_locator import RouteStation


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

    def optimize(
        self, 
        total_route_distance_miles: float, 
        route_stations: List[RouteStation]
    ) -> List[FuelStop]:
        """
        Applies a greedy algorithm to minimize fuel costs.
        
        Assumes we start with a full tank.
        At any given station, we look ahead to all reachable stations.
        If we find a cheaper station, we buy just enough fuel to reach it.
        If no cheaper station is reachable, we fill up completely, and plan
        our next stop at the cheapest reachable station.
        
        Args:
            total_route_distance_miles: Length of the entire route.
            route_stations: List of stations ordered by distance along route.
            
        Returns:
            List of FuelStop objects.
        """
        # If we can reach the destination without stopping
        if total_route_distance_miles <= self.max_range_miles:
            return []

        # Add a dummy "destination" station for the algorithm's end condition
        # We set its price to 0 so the algorithm always prefers to reach it if possible
        # without buying extra fuel
        destination_dummy = RouteStation(
            station=FuelStation(truckstop_name="Destination", retail_price=0.0),
            distance_along_route_miles=total_route_distance_miles,
            distance_from_route_miles=0.0
        )
        
        all_stops = route_stations + [destination_dummy]
        
        current_fuel_gallons = self.max_gallons
        current_position_miles = 0.0
        
        planned_stops: List[FuelStop] = []
        current_stop_index = -1 # Start at origin (not in list)
        
        while True:
            max_reachable_distance = current_position_miles + self.max_range_miles
            
            # If we can reach the destination from current position with FULL tank
            # Wait, the algorithm states we start with full tank and fill up when needed.
            # Let's find all reachable stops from current position
            reachable_stops = []
            for i in range(current_stop_index + 1, len(all_stops)):
                stop = all_stops[i]
                if stop.distance_along_route_miles <= max_reachable_distance:
                    reachable_stops.append((i, stop))
                else:
                    break
                    
            if not reachable_stops:
                raise FuelOptimizationError(
                    f"No reachable stations from mile {current_position_miles:.1f}. "
                    f"Next station is too far."
                )
                
            # Are we looking at the origin? (current_stop_index == -1)
            # Or are we at a station?
            current_price = None
            if current_stop_index >= 0:
                current_price = all_stops[current_stop_index].station.retail_price
                
            # If destination is reachable, and we are not at a station (i.e. at origin),
            # we just go there.
            destination_reachable = any(s[1] == destination_dummy for s in reachable_stops)
            
            if destination_reachable:
                # Can we reach it with CURRENT fuel?
                dist_to_dest = total_route_distance_miles - current_position_miles
                if (current_fuel_gallons * self.mpg) >= dist_to_dest:
                    break # We've made it!
                    
            # We must stop to refuel. 
            # If we are at the origin (-1), we don't buy fuel here (start full).
            # We must pick the next stop.
            if current_stop_index == -1:
                # We want to go as far as possible to the CHEAPEST station in range
                # Filter out destination if we can't reach it with current fuel
                valid_stops = [s for s in reachable_stops if s[1] != destination_dummy]
                if not valid_stops:
                    raise FuelOptimizationError("Cannot reach any valid fuel station from start.")
                    
                # Pick the cheapest reachable station
                best_next = min(valid_stops, key=lambda x: float(x[1].station.retail_price))
                next_index, next_stop = best_next
                
                # Move to it
                dist_traveled = next_stop.distance_along_route_miles - current_position_miles
                current_fuel_gallons -= (dist_traveled / self.mpg)
                current_position_miles = next_stop.distance_along_route_miles
                current_stop_index = next_index
                continue
                
            # We are AT a station. We need to buy fuel.
            # Find if there is a cheaper station ahead.
            cheaper_stop = None
            for idx, stop in reachable_stops:
                if float(stop.station.retail_price) < float(current_price):
                    cheaper_stop = (idx, stop)
                    break
                    
            if cheaper_stop:
                # There is a cheaper station. Buy just enough fuel to reach it.
                next_index, next_stop = cheaper_stop
                dist_to_next = next_stop.distance_along_route_miles - current_position_miles
                gallons_needed_for_trip = dist_to_next / self.mpg
                
                gallons_to_buy = max(0.0, gallons_needed_for_trip - current_fuel_gallons)
                
                if gallons_to_buy > 0:
                    planned_stops.append(
                        FuelStop(
                            station=all_stops[current_stop_index].station,
                            gallons_purchased=gallons_to_buy,
                            cost=gallons_to_buy * float(current_price)
                        )
                    )
                    current_fuel_gallons += gallons_to_buy
                    
                # Move to cheaper station
                current_fuel_gallons -= (dist_to_next / self.mpg)
                current_position_miles = next_stop.distance_along_route_miles
                current_stop_index = next_index
                
            else:
                # No cheaper station reachable. Fill up completely!
                gallons_to_buy = self.max_gallons - current_fuel_gallons
                
                if gallons_to_buy > 0:
                    planned_stops.append(
                        FuelStop(
                            station=all_stops[current_stop_index].station,
                            gallons_purchased=gallons_to_buy,
                            cost=gallons_to_buy * float(current_price)
                        )
                    )
                    current_fuel_gallons = self.max_gallons
                    
                # Now pick the cheapest station from the reachable ones to be our next stop
                # (excluding the one we are currently at, obviously)
                valid_stops = [s for s in reachable_stops if s[1] != destination_dummy]
                
                if destination_reachable:
                    # We have a full tank, so we can definitely reach destination now
                    # (since destination is in reachable_stops, it's <= max_range)
                    break 
                    
                if not valid_stops:
                    raise FuelOptimizationError(f"Stuck at mile {current_position_miles:.1f}")
                    
                # Pick the cheapest one to go to next
                # If there are multiple with same price, pick the furthest one to minimize stops
                # But since Python's min() returns the first one it encounters, and our list is
                # ordered by distance, it picks the first one. Let's explicitly pick furthest if tied.
                def sort_key(x):
                    return (float(x[1].station.retail_price), -x[1].distance_along_route_miles)
                    
                best_next = min(valid_stops, key=sort_key)
                next_index, next_stop = best_next
                
                # Move to it
                dist_to_next = next_stop.distance_along_route_miles - current_position_miles
                current_fuel_gallons -= (dist_to_next / self.mpg)
                current_position_miles = next_stop.distance_along_route_miles
                current_stop_index = next_index

        # Clean up any stops with 0 gallons (can happen if logic leads to just stopping but not buying)
        planned_stops = [s for s in planned_stops if s.gallons_purchased > 0]
        return planned_stops
