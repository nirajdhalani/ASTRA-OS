import math
from datetime import datetime, timezone


def norm360(value: float) -> float:
    return value % 360.0


def angular_difference(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def sign_index(longitude: float) -> int:
    return int(norm360(longitude) // 30)


def sign_degree(longitude: float) -> float:
    return norm360(longitude) % 30.0


def julian_day(dt: datetime) -> float:
    """Gregorian calendar to Julian Day, using UTC input."""
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    dt = dt.astimezone(timezone.utc)
    year, month = dt.year, dt.month
    day = dt.day + (dt.hour + (dt.minute + (dt.second + dt.microsecond / 1e6) / 60) / 60) / 24
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5


def lahiri_ayanamsa(jd: float) -> float:
    """Mean Chitrapaksha approximation, degrees; epoch anchor 1900-01-01.0."""
    t = (jd - 2415020.0) / 36525.0
    # Lahiri mean value at the anchor plus precession rate and a small quadratic term.
    seconds = (22 * 3600 + 27 * 60 + 37.7) + 50.2388475 * (jd - 2415020.0) / 365.2422 + 0.00011175 * ((jd - 2415020.0) / 36525.0) ** 2
    return seconds / 3600.0


def ayanamsa_value(kind: str, jd: float) -> float:
    lahiri = lahiri_ayanamsa(jd)
    if kind == "lahiri":
        return lahiri
    if kind == "kp":
        # KP ayanamsa is modelled as the published 5′47.7″ offset from Lahiri mean.
        return lahiri - (5.0 + 47.7 / 60.0) / 60.0
    if kind == "raman":
        return lahiri - (1.0 + 27.0 / 60.0)
    if kind == "fagan_bradley":
        # Fixed offset anchored to commonly tabulated Fagan-Bradley/Lahiri difference.
        return lahiri + 0.88
    if kind == "tropical":
        return 0.0
    raise ValueError(f"Unsupported ayanamsa: {kind}")


def nakshatra_data(longitude: float) -> dict:
    from .constants import NAKSHATRAS, NAKSHATRA_LORDS
    span = 360.0 / 27.0
    position = norm360(longitude)
    index = min(26, int(position / span))
    within = position - index * span
    pada = min(4, int(within / (span / 4)) + 1)
    return {
        "index": index,
        "name": NAKSHATRAS[index],
        "lord": NAKSHATRA_LORDS[index],
        "pada": pada,
        "progress_percent": round(within / span * 100.0, 5),
        "degrees_into": round(within, 6),
    }


def format_dms(decimal_degrees: float) -> str:
    d = int(decimal_degrees)
    minutes_full = (decimal_degrees - d) * 60
    m = int(minutes_full)
    s = (minutes_full - m) * 60
    return f"{d}° {m:02d}′ {s:04.1f}″"
