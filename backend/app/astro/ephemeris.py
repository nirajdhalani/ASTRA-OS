from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .math_utils import norm360

EPHEMERIS_START_YEAR = 1849
EPHEMERIS_END_YEAR = 2150


class EphemerisUnavailable(RuntimeError):
    pass


# DE440s exposes the outer planets as system barycentres. In particular, it
# contains target 4 (MARS BARYCENTER), not target 499 (Mars' centre).
# Candidate lists keep the provider compatible with kernels that expose a
# planet centre as well as with DE440s.
BODY_KEY_CANDIDATES = {
    "Sun": ("sun",),
    "Moon": ("moon",),
    "Mercury": ("mercury", "mercury barycenter"),
    "Venus": ("venus", "venus barycenter"),
    "Mars": ("mars", "mars barycenter"),
    "Jupiter": ("jupiter barycenter", "jupiter"),
    "Saturn": ("saturn barycenter", "saturn"),
    "Uranus": ("uranus barycenter", "uranus"),
    "Neptune": ("neptune barycenter", "neptune"),
    "Pluto": ("pluto barycenter", "pluto"),
}


def resolve_body_keys(kernel) -> dict[str, str]:
    """Resolve application body names to targets actually present in a kernel."""
    resolved: dict[str, str] = {}
    for body_name, candidates in BODY_KEY_CANDIDATES.items():
        for candidate in candidates:
            try:
                kernel[candidate]
            except KeyError:
                continue
            resolved[body_name] = candidate
            break
        else:
            tried = ", ".join(repr(candidate) for candidate in candidates)
            raise EphemerisUnavailable(
                f"The loaded JPL kernel does not contain a target for {body_name}. "
                f"Tried: {tried}. Use a compatible DE440s kernel."
            )
    return resolved


class SkyfieldProvider:
    """Apparent geocentric ecliptic-of-date positions from JPL DE440s."""
    def __init__(self, data_dir: str | Path, filename: str = "de440s.bsp"):
        try:
            from skyfield.api import Loader
            self._loader = Loader(str(data_dir))
            self._ts = self._loader.timescale(builtin=True)
            # Skyfield's Loader knows the official URL for named JPL kernels.
            self._kernel = self._loader(filename)
            self._body_keys = resolve_body_keys(self._kernel)
            from skyfield.framelib import ecliptic_frame
            self._ecliptic_frame = ecliptic_frame
        except EphemerisUnavailable:
            raise
        except Exception as exc:
            raise EphemerisUnavailable(
                "JPL DE440s ephemeris could not be loaded. Run `python scripts/download_ephemeris.py` with network access, then restart ASTRA OS. "
                f"Underlying error: {exc}"
            ) from exc

    def _time(self, utc_dt: datetime):
        if utc_dt.tzinfo is None:
            raise ValueError("UTC datetime must be timezone-aware")
        return self._ts.from_datetime(utc_dt.astimezone(timezone.utc))

    def longitude(self, body_name: str, utc_dt: datetime) -> float:
        try:
            body_key = self._body_keys[body_name]
        except KeyError as exc:
            raise ValueError(f"Unsupported solar-system body: {body_name}") from exc
        t = self._time(utc_dt)
        position = self._kernel["earth"].at(t).observe(self._kernel[body_key]).apparent()
        _, lon, _ = position.frame_latlon(self._ecliptic_frame)
        return norm360(float(lon.degrees))

    def positions(self, utc_dt: datetime) -> dict[str, dict]:
        result = {}
        for name in BODY_KEY_CANDIDATES:
            longitude = self.longitude(name, utc_dt)
            before = self.longitude(name, utc_dt - timedelta(hours=12))
            after = self.longitude(name, utc_dt + timedelta(hours=12))
            delta = (after - before + 180.0) % 360.0 - 180.0
            result[name] = {"tropical_longitude": longitude, "speed_degrees_per_day": delta}
        return result

    def gast_degrees(self, utc_dt: datetime) -> float:
        return float(self._time(utc_dt).gast) * 15.0
