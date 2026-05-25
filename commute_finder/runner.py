import os
from datetime import datetime
from typing import Callable

from commute_finder.communes import load_communes, prefilter_communes
from commute_finder.distance import calculate_travel_times
from commute_finder.geocoding import geocode_location
from commute_finder.map_builder import build_map


def rebuild_for_limit(
    communes: list[dict],
    destinations: list[dict],
    max_time: int,
    mode: str,
    output: str,
) -> tuple[list[dict], str]:
    """Re-evaluate reachability with a new time limit and rebuild the map. No API calls."""
    limit_seconds = max_time * 60
    for commune in communes:
        max_t = commune.get("max_travel_time")
        commune["reachable"] = max_t is not None and max_t <= limit_seconds

    reachable = [c for c in communes if c["reachable"]]
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    build_map(communes, reachable, destinations, max_time, mode, output)
    return reachable, output


def run_analysis(
    locations: list[str],
    max_time: int,
    mode: str,
    api_key: str,
    output: str | None = None,
    log: Callable[[str], None] = print,
) -> tuple[list[dict], str, list[dict], list[dict]]:
    """
    Run the full commute analysis. Returns (reachable_communes, output_path).
    Raises ValueError for bad inputs (geocoding failure, no locations, etc.).
    """
    if output is None:
        ts = datetime.now().strftime("%y%m%d_%H%M")
        output = f"output/{ts}_commute_map.html"

    # 1. Geocode destinations
    log("Geocoding destinations...")
    destinations = []
    for loc in locations:
        coords = geocode_location(loc, api_key)
        if not coords:
            raise ValueError(f"Could not geocode '{loc}'. Check the address and try again.")
        destinations.append({"name": loc, "lat": coords[0], "lng": coords[1]})
        log(f"  {loc}  ->  ({coords[0]:.5f}, {coords[1]:.5f})")

    # 2. Load commune/quartier boundaries
    log("\nLoading area data...")
    communes = load_communes(verbose=False)
    log(f"  {len(communes)} areas loaded")
    communes = prefilter_communes(communes, destinations, mode)
    log(f"  {len(communes)} areas within straight-line range")

    if not communes:
        log("\nNo areas within range. Try increasing max time.")
        return [], output, [], destinations

    # 3. Query travel times
    log(f"\nQuerying travel times ({mode})...")
    for dest in destinations:
        log(f"  From: {dest['name']}  ({len(communes)} areas)...")
        dest["travel_times"] = calculate_travel_times(
            origin=(dest["lat"], dest["lng"]),
            communes=communes,
            mode=mode,
            api_key=api_key,
        )

    # 4. Annotate each area with worst-case commute across all destinations
    limit_seconds = max_time * 60
    for commune in communes:
        code = commune["code"]
        times = [dest["travel_times"].get(code) for dest in destinations]
        if any(t is None for t in times):
            commune["max_travel_time"] = None
            commune["reachable"] = False
        else:
            worst = max(times)
            commune["max_travel_time"] = worst
            commune["reachable"] = worst <= limit_seconds
        commune["travel_times_by_dest"] = {
            dest["name"]: dest["travel_times"].get(code) for dest in destinations
        }

    reachable = [c for c in communes if c["reachable"]]
    log(f"\n  {len(reachable)} areas within {max_time} min from all destinations")

    # 5. Build map
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    log(f"\nBuilding map -> {output}...")
    build_map(communes, reachable, destinations, max_time, mode, output)
    log(f"Map saved: {output}")

    return reachable, output, communes, destinations
