from functools import lru_cache
from fastapi import APIRouter, HTTPException, Query
from ..config import settings

router = APIRouter(prefix="/api", tags=["geography"])


@lru_cache(maxsize=1)
def _nominatim_geocode():
    from geopy.geocoders import Nominatim
    from geopy.extra.rate_limiter import RateLimiter
    geolocator = Nominatim(user_agent=settings.geocoder_user_agent, timeout=12)
    return RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=1, swallow_exceptions=False)


@lru_cache(maxsize=1)
def _mapbox_geolocator():
    from geopy.geocoders import MapBox
    if not settings.geocoder_api_key:
        raise RuntimeError("ASTRA_GEOCODER_API_KEY is required when ASTRA_GEOCODER_PROVIDER=mapbox")
    return MapBox(api_key=settings.geocoder_api_key, timeout=12)


@lru_cache(maxsize=512)
def _lookup(query: str) -> list[dict]:
    try:
        if settings.geocoder_provider.lower() == "mapbox":
            results = _mapbox_geolocator().geocode(query, exactly_one=False)
            output = []
            for location in (results or []):
                output.append({
                    "label": location.address,
                    "latitude": float(location.latitude),
                    "longitude": float(location.longitude),
                    "provider": "mapbox",
                })
            return output

        if settings.geocoder_provider.lower() != "nominatim":
            raise RuntimeError("Unsupported geocoder provider. Use nominatim or mapbox.")
        results = _nominatim_geocode()(query, exactly_one=False, limit=5, addressdetails=True)
        output = []
        for location in (results or []):
            output.append({
                "label": location.address,
                "latitude": float(location.latitude),
                "longitude": float(location.longitude),
                "osm_type": getattr(location, "raw", {}).get("osm_type"),
                "osm_id": getattr(location, "raw", {}).get("osm_id"),
                "provider": "nominatim",
            })
        return output
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


@router.get("/geocode")
def geocode(query: str = Query(min_length=2, max_length=180)):
    try:
        return {"results": _lookup(query.strip()), "provider": settings.geocoder_provider.lower()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Place lookup is temporarily unavailable. Enter coordinates and timezone manually.") from exc


@lru_cache(maxsize=1)
def _timezone_finder():
    from timezonefinder import TimezoneFinder
    return TimezoneFinder(in_memory=True)


@router.get("/timezone")
def timezone_for_coordinates(latitude: float = Query(ge=-90, le=90), longitude: float = Query(ge=-180, le=180)):
    try:
        zone = _timezone_finder().timezone_at(lat=latitude, lng=longitude)
        if not zone:
            raise HTTPException(status_code=404, detail="No timezone polygon found for these coordinates")
        return {"timezone": zone}
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Timezone lookup dependency is not installed") from exc
