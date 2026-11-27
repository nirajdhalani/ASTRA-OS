import math
from .math_utils import norm360, sign_index


def _equatorial_from_ecliptic(longitude: float, obliquity: float) -> tuple[float, float]:
    lam = math.radians(longitude)
    eps = math.radians(obliquity)
    x = math.cos(lam)
    y = math.sin(lam) * math.cos(eps)
    z = math.sin(lam) * math.sin(eps)
    ra = math.degrees(math.atan2(y, x)) % 360.0
    dec = math.degrees(math.asin(max(-1.0, min(1.0, z))))
    return ra, dec


def _hour_angle(ra: float, lst: float) -> float:
    return (lst - ra + 180.0) % 360.0 - 180.0


def _ascendant_and_mc(lst_degrees: float, latitude: float, obliquity: float) -> tuple[float, float]:
    theta = math.radians(lst_degrees)
    phi = math.radians(latitude)
    eps = math.radians(obliquity)
    # Intersection of the ecliptic with the local east horizon.
    a = math.cos(phi) * math.cos(theta)
    b = math.sin(phi) * math.sin(eps) + math.cos(phi) * math.cos(eps) * math.sin(theta)
    candidates = [math.degrees(math.atan2(-a, b)) % 360.0]
    candidates.append((candidates[0] + 180.0) % 360.0)
    asc_candidates = []
    for candidate in candidates:
        ra, _ = _equatorial_from_ecliptic(candidate, obliquity)
        h = _hour_angle(ra, lst_degrees)
        if h < 0:
            asc_candidates.append((candidate, h))
    if not asc_candidates:
        asc = candidates[0]
    else:
        # The rising point is the eastern-horizon intersection, H<0; closest to due east.
        asc = min(asc_candidates, key=lambda item: abs(item[1]))[0]
    mc = math.degrees(math.atan2(math.sin(theta), math.cos(theta) * math.cos(eps))) % 360.0
    return norm360(asc), norm360(mc)


def _placidus_intermediate(target: str, lst: float, latitude: float, obliquity: float) -> float:
    phi = math.radians(latitude)

    def residual(lam: float) -> float | None:
        ra, dec = _equatorial_from_ecliptic(lam, obliquity)
        raw = -math.tan(phi) * math.tan(math.radians(dec))
        if raw < -1.0 or raw > 1.0:
            return None
        semi_arc = math.degrees(math.acos(raw))
        hour = _hour_angle(ra, lst)
        if target == "11":
            desired = -semi_arc / 3.0
        elif target == "12":
            desired = -2.0 * semi_arc / 3.0
        elif target == "2":
            desired = -semi_arc - (180.0 - semi_arc) / 3.0
        else:  # house 3
            desired = -semi_arc - 2.0 * (180.0 - semi_arc) / 3.0
        return hour - desired

    # Find and refine every genuine zero. A wrapped hour-angle jump at ±180° can
    # also change sign; reject that discontinuity by checking the refined residual.
    roots: list[tuple[float, float]] = []
    previous_x = None
    previous_y = None
    for step in range(721):
        x = step * 0.5
        y = residual(x)
        if y is None:
            previous_x, previous_y = None, None
            continue
        if previous_y is not None and y * previous_y <= 0.0:
            lo, hi = previous_x, x
            flo = previous_y
            valid = True
            for _ in range(70):
                mid = (lo + hi) / 2.0
                fm = residual(mid)
                if fm is None:
                    valid = False
                    break
                if abs(fm) < 1e-10:
                    lo = hi = mid
                    break
                if flo * fm <= 0.0:
                    hi = mid
                else:
                    lo, flo = mid, fm
            root = (lo + hi) / 2.0
            final_residual = residual(root)
            if valid and final_residual is not None and abs(final_residual) < 1e-5:
                ra, _ = _equatorial_from_ecliptic(root, obliquity)
                hour = _hour_angle(ra, lst)
                if -179.999 < hour < -0.001:
                    roots.append((root, hour))
        previous_x, previous_y = x, y

    if not roots:
        raise ValueError("Placidus houses are undefined for this latitude/date (circumpolar geometry). Select Equal or Whole Sign houses.")
    wanted_hour = {"11": -55.0, "12": -115.0, "2": -125.0, "3": -150.0}[target]
    return norm360(min(roots, key=lambda item: abs(item[1] - wanted_hour))[0])


def calculate_houses(lst_degrees: float, latitude: float, obliquity: float, house_system: str, sidereal_offset: float = 0.0) -> dict:
    if not -66.0 <= latitude <= 66.0 and house_system == "placidus":
        raise ValueError("Placidus is unreliable at this latitude; choose Equal or Whole Sign houses.")
    asc_tropical, mc_tropical = _ascendant_and_mc(lst_degrees, latitude, obliquity)
    if house_system == "whole_sign":
        asc = norm360(asc_tropical - sidereal_offset)
        first_sign = sign_index(asc)
        cusps = [norm360((first_sign + i) * 30.0 - 0.0) for i in range(12)]
        # Whole-sign cusps begin at 0° of the rising sign.
    elif house_system == "equal":
        cusps = [norm360(asc_tropical - sidereal_offset + i * 30.0) for i in range(12)]
    elif house_system == "placidus":
        c11 = _placidus_intermediate("11", lst_degrees, latitude, obliquity)
        c12 = _placidus_intermediate("12", lst_degrees, latitude, obliquity)
        c2 = _placidus_intermediate("2", lst_degrees, latitude, obliquity)
        c3 = _placidus_intermediate("3", lst_degrees, latitude, obliquity)
        tropical = [asc_tropical, c2, c3, norm360(mc_tropical + 180), norm360(c11 + 180), norm360(c12 + 180), norm360(asc_tropical + 180), norm360(c2 + 180), norm360(c3 + 180), mc_tropical, c11, c12]
        cusps = [norm360(x - sidereal_offset) for x in tropical]
    else:
        raise ValueError(f"Unsupported house system: {house_system}")
    if house_system == "whole_sign":
        mc = norm360(mc_tropical - sidereal_offset)
    else:
        mc = norm360(mc_tropical - sidereal_offset)
    asc_sidereal = norm360(asc_tropical - sidereal_offset)
    return {
        "system": house_system,
        "ascendant": round(asc_sidereal, 6),
        "midheaven": round(mc, 6),
        "cusps": [round(x, 6) for x in cusps],
        "tropical_ascendant": round(asc_tropical, 6),
        "tropical_midheaven": round(mc_tropical, 6),
    }


def house_for_longitude(longitude: float, cusps: list[float], house_system: str) -> int:
    longitude %= 360.0
    if house_system == "whole_sign":
        return (int(longitude // 30) - int(cusps[0] // 30)) % 12 + 1
    for index, start in enumerate(cusps):
        end = cusps[(index + 1) % 12]
        span = (end - start) % 360.0
        offset = (longitude - start) % 360.0
        if offset < span or (span == 0 and offset == 0):
            return index + 1
    return 12
