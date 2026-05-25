import time
from datetime import datetime, timedelta

import googlemaps

_BATCH_SIZE = 25  # Distance Matrix API hard limit per request


def _next_weekday_morning_ts() -> int:
    """Unix timestamp for next Monday at 08:30 local time (typical morning commute)."""
    now = datetime.now()
    days_ahead = (7 - now.weekday()) % 7 or 7  # always at least 1 day ahead
    target = (now + timedelta(days=days_ahead)).replace(hour=8, minute=30, second=0, microsecond=0)
    return int(target.timestamp())


def calculate_travel_times(
    origin: tuple[float, float],
    communes: list[dict],
    mode: str,
    api_key: str,
) -> dict[str, int | None]:
    """
    Return {commune_code: duration_seconds | None} from origin to each commune centroid.
    Batches requests to respect the 25-element-per-request limit.
    """
    client = googlemaps.Client(key=api_key)
    departure = _next_weekday_morning_ts() if mode == "transit" else None
    results: dict[str, int | None] = {}

    for i in range(0, len(communes), _BATCH_SIZE):
        batch = communes[i : i + _BATCH_SIZE]
        destinations_coords = [(c["lat"], c["lng"]) for c in batch]

        kwargs: dict = dict(origins=[origin], destinations=destinations_coords, mode=mode)
        if departure:
            kwargs["departure_time"] = departure

        try:
            resp = client.distance_matrix(**kwargs)
            elements = resp["rows"][0]["elements"]
            for commune, el in zip(batch, elements):
                if el["status"] == "OK":
                    results[commune["code"]] = el["duration"]["value"]
                else:
                    results[commune["code"]] = None
        except Exception:
            for commune in batch:
                results[commune["code"]] = None

        # Stay well below the 50 QPS default quota
        if i + _BATCH_SIZE < len(communes):
            time.sleep(0.05)

    return results
