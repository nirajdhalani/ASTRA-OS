from __future__ import annotations
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .constants import PLANETS, VARGAS, SIGNS, SIGNS_HI, SIGNS_GU
from .divisional import divisional_charts
from .dasha import vimshottari_dasha
from .ephemeris import SkyfieldProvider, EPHEMERIS_START_YEAR, EPHEMERIS_END_YEAR
from .houses import calculate_houses, house_for_longitude
from .interpretations import build_domain_reports
from .math_utils import ayanamsa_value, format_dms, julian_day, nakshatra_data, norm360, sign_degree, sign_index
from .panchang import calculate_panchang
from .systems import (
    detect_yogas_and_doshas, jaimini_chara_karakas, jaimini_rashi_drishti,
    kp_sub_lords, planetary_dignities, vedic_aspects, western_aspects,
)


class ChartCalculationError(RuntimeError):
    pass


def mean_lunar_node(jd: float) -> float:
    """Mean ascending lunar node, polynomial in Julian centuries from J2000."""
    t = (jd - 2451545.0) / 36525.0
    return norm360(125.0445479 - 1934.1362891 * t + 0.0020754 * t * t + t**3 / 467441.0 - t**4 / 60616000.0)


def mean_obliquity_degrees(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    arcseconds = 84381.448 - 46.8150 * t - 0.00059 * t * t + 0.001813 * t**3
    return arcseconds / 3600.0


def _localize_sign(longitude: float, locale: str) -> str:
    idx = sign_index(longitude)
    return {"en": SIGNS, "hi": SIGNS_HI, "gu": SIGNS_GU}[locale][idx]


def _default_house_system(system: str) -> str:
    return "placidus" if system in ("western", "kp") else "whole_sign"


def build_chart(payload: dict[str, Any], birth_utc: datetime, provider: Any, now_utc: datetime | None = None) -> dict:
    if birth_utc.year < EPHEMERIS_START_YEAR or birth_utc.year > EPHEMERIS_END_YEAR:
        raise ChartCalculationError(f"This build uses JPL DE440s, which supports approximately {EPHEMERIS_START_YEAR}–{EPHEMERIS_END_YEAR}. Requested year: {birth_utc.year}.")
    jd = julian_day(birth_utc)
    chart_system = payload.get("chart_system", "vedic")
    locale = payload.get("locale", "en")
    ayanamsa_name = "kp" if chart_system == "kp" else payload.get("ayanamsa", "lahiri")
    if chart_system == "western":
        ayanamsa_name = "tropical"
    ayanamsa = ayanamsa_value(ayanamsa_name, jd)
    house_system = payload.get("house_system") or _default_house_system(chart_system)

    raw = provider.positions(birth_utc)
    raw["Rahu"] = {"tropical_longitude": mean_lunar_node(jd), "speed_degrees_per_day": -0.05295}
    raw["Ketu"] = {"tropical_longitude": norm360(raw["Rahu"]["tropical_longitude"] + 180.0), "speed_degrees_per_day": -0.05295}
    if chart_system == "western":
        active_names = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    else:
        active_names = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    positions: dict[str, dict] = {}
    for name in active_names:
        data = raw[name]
        tropical = norm360(float(data["tropical_longitude"]))
        sidereal = norm360(tropical - ayanamsa)
        longitude = tropical if chart_system == "western" else sidereal
        nak = nakshatra_data(sidereal) if chart_system != "western" else None
        positions[name] = {
            "tropical_longitude": round(tropical, 7),
            "sidereal_longitude": round(sidereal, 7),
            "longitude": round(longitude, 7),
            "sign_index": sign_index(longitude),
            "sign": _localize_sign(longitude, locale),
            "degree_in_sign": round(sign_degree(longitude), 6),
            "degree_dms": format_dms(sign_degree(longitude)),
            "speed_degrees_per_day": round(float(data.get("speed_degrees_per_day", 0.0)), 7),
            "retrograde": float(data.get("speed_degrees_per_day", 0.0)) < -0.0001,
            "nakshatra": nak,
        }

    # Western charts use tropical longitude; Vedic families use sidereal longitudes.
    houses = calculate_houses(
        lst_degrees=(provider.gast_degrees(birth_utc) + float(payload["longitude"])) % 360.0,
        latitude=float(payload["latitude"]),
        obliquity=mean_obliquity_degrees(jd),
        house_system=house_system,
        sidereal_offset=ayanamsa,
    )
    houses["ascendant_sign_index"] = sign_index(houses["ascendant"])
    houses["ascendant_sign"] = _localize_sign(houses["ascendant"], locale)
    houses["midheaven_sign_index"] = sign_index(houses["midheaven"])
    houses["midheaven_sign"] = _localize_sign(houses["midheaven"], locale)
    houses["cusp_sign_indices"] = [sign_index(cusp) for cusp in houses["cusps"]]
    houses["cusp_signs"] = [_localize_sign(cusp, locale) for cusp in houses["cusps"]]
    house_map = {}
    for name, data in positions.items():
        house_map[name] = house_for_longitude(data["longitude"], houses["cusps"], house_system)
        data["house"] = house_map[name]

    # Dignities are a Vedic framework. For Western charts this is informational only.
    if chart_system != "western":
        dignities = planetary_dignities(positions)
        for name, dignity in dignities.items():
            positions[name]["dignity"] = dignity["dignity"]
    else:
        for name in positions:
            positions[name]["dignity"] = "not_applicable"

    # Divisional charts use sidereal longitudes and are included for the Vedic systems.
    if chart_system == "western":
        varga_data = {}
    else:
        varga_data = divisional_charts(positions, houses["ascendant"], VARGAS)

    aspects = {
        "western": western_aspects(positions) if chart_system == "western" else [],
        "vedic": vedic_aspects(positions, houses, lambda lon, cusps, hs: house_for_longitude(lon, cusps, hs)) if chart_system != "western" else [],
    }
    yogas = detect_yogas_and_doshas(positions, houses, house_map) if chart_system != "western" else []
    jaimini = {}
    if chart_system == "jaimini":
        jaimini = {
            "chara_karakas_8": jaimini_chara_karakas(positions, include_rahu=True),
            "chara_karakas_7": jaimini_chara_karakas(positions, include_rahu=False),
            "rashi_drishti": jaimini_rashi_drishti(),
        }
    kp = {}
    if chart_system == "kp":
        kp = {
            "planetary_sub_lords": {name: kp_sub_lords(data["sidereal_longitude"]) for name, data in positions.items()},
            "cusp_sub_lords": [
                {"house": i + 1, "longitude": cusp, **kp_sub_lords(cusp)} for i, cusp in enumerate(houses["cusps"])
            ],
        }

    moon_for_dasha = positions.get("Moon", {}).get("sidereal_longitude")
    analysis_time = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    dasha = vimshottari_dasha(moon_for_dasha, birth_utc, now_utc=analysis_time, cycles=4) if chart_system != "western" and moon_for_dasha is not None else None
    panchang = calculate_panchang(
        positions["Sun"]["sidereal_longitude"],
        positions["Moon"]["sidereal_longitude"],
        birth_utc.weekday(),
    ) if chart_system != "western" else None
    domains = build_domain_reports(positions, houses, house_map, locale) if chart_system != "western" else []

    return {
        "product": "ASTRA OS",
        "engine_version": "0.1.1",
        "birth": {
            "local_date": payload["birth_date"],
            "local_time": payload["birth_time"],
            "place": payload["place"],
            "latitude": payload["latitude"],
            "longitude": payload["longitude"],
            "timezone": payload["timezone_name"],
            "utc_datetime": birth_utc.astimezone(timezone.utc).isoformat(),
            "julian_day_utc": round(jd, 8),
            "analysis_timestamp_utc": analysis_time.isoformat(),
        },
        "configuration": {
            "chart_system": chart_system,
            "ayanamsa": ayanamsa_name,
            "ayanamsa_degrees": round(ayanamsa, 8),
            "house_system": house_system,
            "ephemeris": "JPL DE440s via Skyfield",
            "node_method": "mean lunar node",
            "locale": locale,
            "varga_set": VARGAS if chart_system != "western" else [],
            "conventions": [
                "Geocentric apparent planetary positions in the true ecliptic and equinox of date.",
                "Mean lunar node polynomial; Ketu is exactly opposite Rahu.",
                "Lahiri/KP/Raman/Fagan-Bradley ayanamsa values are implementation models; match the named convention and version before claiming parity with another program.",
                "Dasha calendar year is 365.2425 days.",
            ],
        },
        "houses": houses,
        "planetary_positions": positions,
        "house_occupancy": house_map,
        "divisional_charts": varga_data,
        "aspects": aspects,
        "yogas_and_doshas": yogas,
        "vimshottari_dasha": dasha,
        "panchang": panchang,
        "kp_analysis": kp,
        "jaimini_analysis": jaimini,
        "life_domains": domains,
        "quality": {
            "calculation_status": "calculated",
            "birth_time_precision": "user_supplied",
            "coordinate_precision": "provided_or_geocoded; verify birthplace pin for historical records",
            "ephemeris_coverage": f"{EPHEMERIS_START_YEAR}-{EPHEMERIS_END_YEAR}",
            "prediction_certainty": "not_quantifiable; astrology is an interpretive tradition, not an empirically validated event-prediction method",
            "warnings": [
                "Birth-time errors can change the Ascendant, house cusps and divisional-chart placements.",
                "No chart configuration can guarantee future events or medical, legal, financial or relationship outcomes.",
            ],
        },
    }
