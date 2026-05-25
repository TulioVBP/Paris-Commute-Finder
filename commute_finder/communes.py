import json
import os
from math import atan2, cos, radians, sin, sqrt

import requests

_CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "communes_paris_region.geojson")

_FIELDS = "nom,code,population"
_FMT = "format=geojson&geometry=contour"
_BASE = "https://geo.api.gouv.fr/communes"

# Paris: 80 quartiers from OpenData Paris (finer than the 20 arrondissements)
_PARIS_URL = (
    "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets"
    "/quartier_paris/exports/geojson?lang=fr&timezone=Europe%2FParis"
)

# Petite couronne (92, 93, 94) + grande couronne (77, 78, 91, 95)
_DEPT_URLS = [
    f"{_BASE}?codeDepartement={d}&fields={_FIELDS}&{_FMT}"
    for d in ["92", "93", "94", "77", "78", "91", "95"]
]

_MODE_RADIUS_KM = {
    "transit": 10,
    "walking": 10,
    "bicycling": 28,
}


def _fetch_features(url: str) -> list[dict]:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        return data.get("features", [])
    if isinstance(data, list):
        return data
    return []


def _feature_to_commune(feature: dict) -> dict | None:
    props = feature.get("properties", {})
    geometry = feature.get("geometry")
    lat, lng = _geometry_centroid(geometry)
    if lat is None:
        return None

    # Paris quartier format (opendata.paris.fr): fields l_qu / c_quinsee
    if "l_qu" in props:
        arr = props.get("c_ar")
        arr_label = f" ({arr}{'er' if arr == 1 else 'e'})" if arr else ""
        return {
            "code": str(props.get("c_quinsee", props.get("c_qu", ""))),
            "nom": props.get("l_qu", "") + arr_label,
            "population": 0,
            "lat": lat,
            "lng": lng,
            "geometry": geometry,
        }

    # Standard geo.api.gouv.fr format
    code = props.get("code", "")
    if not code:
        return None
    return {
        "code": code,
        "nom": props.get("nom", ""),
        "population": props.get("population") or 0,
        "lat": lat,
        "lng": lng,
        "geometry": geometry,
    }


def _geometry_centroid(geometry: dict | None) -> tuple[float | None, float | None]:
    """Return (lat, lng) centroid computed from the polygon outer ring(s)."""
    if not geometry:
        return None, None
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if gtype == "Polygon":
        rings = [coords[0]] if coords else []
    elif gtype == "MultiPolygon":
        rings = [poly[0] for poly in coords if poly]
    else:
        return None, None
    all_pts = [pt for ring in rings for pt in ring]
    if not all_pts:
        return None, None
    lng = sum(pt[0] for pt in all_pts) / len(all_pts)
    lat = sum(pt[1] for pt in all_pts) / len(all_pts)
    return lat, lng


def load_communes(verbose: bool = True) -> list[dict]:
    """
    Return Paris quartiers + surrounding communes with centroid coords and polygon geometry.
    Downloads from geo.api.gouv.fr / opendata.paris.fr on first run and caches locally.
    """
    if os.path.exists(_CACHE_FILE):
        if verbose:
            print("  Loading cached boundaries...", flush=True)
        with open(_CACHE_FILE, encoding="utf-8") as f:
            features = json.load(f)
    else:
        if verbose:
            print("  Downloading Paris quartiers + surrounding communes (one-time)...", flush=True)
        features = _fetch_features(_PARIS_URL)
        for url in _DEPT_URLS:
            features += _fetch_features(url)
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(features, f)
        if verbose:
            print(f"  Cached to data/communes_paris_region.geojson ({len(features)} areas)", flush=True)

    communes = []
    for feature in features:
        commune = _feature_to_commune(feature)
        if commune:
            communes.append(commune)
    return communes


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1.0 - a))


def prefilter_communes(
    communes: list[dict],
    destinations: list[dict],
    mode: str,
) -> list[dict]:
    max_km = _MODE_RADIUS_KM.get(mode, 40)
    result = []
    for commune in communes:
        for dest in destinations:
            if _haversine_km(commune["lat"], commune["lng"], dest["lat"], dest["lng"]) <= max_km:
                result.append(commune)
                break
    return result
