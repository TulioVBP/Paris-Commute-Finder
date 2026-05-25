import googlemaps


def geocode_location(address: str, api_key: str) -> tuple[float, float] | None:
    """Return (lat, lng) for a free-text address, biased to France."""
    client = googlemaps.Client(key=api_key)
    results = client.geocode(address, region="fr", language="fr")
    if not results:
        return None
    loc = results[0]["geometry"]["location"]
    return loc["lat"], loc["lng"]
