from .constants import SIGNS
from .math_utils import angular_difference, norm360, sign_index, sign_degree


RULERS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
EXALTATION = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6}
DEBILITATION = {planet: (sign + 6) % 12 for planet, sign in EXALTATION.items()}


def planet_house_map(positions: dict, houses: dict, house_for_longitude) -> dict:
    return {name: house_for_longitude(data["sidereal_longitude"], houses["cusps"], houses["system"]) for name, data in positions.items()}


def planetary_dignities(positions: dict) -> dict:
    result = {}
    for name, data in positions.items():
        sign = sign_index(data["sidereal_longitude"])
        if name in EXALTATION and sign == EXALTATION[name]:
            dignity = "exalted"
        elif name in DEBILITATION and sign == DEBILITATION[name]:
            dignity = "debilitated"
        elif name in ("Rahu", "Ketu"):
            dignity = "tradition-dependent"
        elif name in RULERS and RULERS[sign] == name:
            dignity = "own_sign"
        else:
            dignity = "neutral"
        result[name] = {"sign": SIGNS[sign], "dignity": dignity}
    return result


def western_aspects(positions: dict) -> list[dict]:
    points = {name: d["tropical_longitude"] for name, d in positions.items() if name not in ("Rahu", "Ketu")}
    definitions = [(0, "conjunction", 8), (60, "sextile", 4), (90, "square", 6), (120, "trine", 6), (150, "quincunx", 3), (180, "opposition", 8)]
    aspects = []
    names = list(points)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            separation = angular_difference(points[a], points[b])
            for exact, label, orb_limit in definitions:
                orb = abs(separation - exact)
                if orb <= orb_limit:
                    aspects.append({"planet_a": a, "planet_b": b, "aspect": label, "exact_degrees": exact, "separation": round(separation, 4), "orb": round(orb, 4)})
                    break
    return aspects


def vedic_aspects(positions: dict, houses: dict, house_for_longitude) -> list[dict]:
    result = []
    for planet, data in positions.items():
        house = house_for_longitude(data["sidereal_longitude"], houses["cusps"], houses["system"])
        offsets = [7]
        if planet == "Mars": offsets = [4, 7, 8]
        elif planet == "Jupiter": offsets = [5, 7, 9]
        elif planet == "Saturn": offsets = [3, 7, 10]
        elif planet in ("Rahu", "Ketu"): offsets = [5, 7, 9]
        for offset in offsets:
            target_house = (house - 1 + offset - 1) % 12 + 1
            result.append({"planet": planet, "from_house": house, "to_house": target_house, "aspect_offset": offset})
    return result


def kp_sub_lords(longitude: float) -> dict:
    from .constants import DASHA_ORDER, DASHA_YEARS, NAKSHATRAS, NAKSHATRA_LORDS
    position = norm360(longitude)
    nak_span = 360.0 / 27.0
    nak_index = min(26, int(position / nak_span))
    fraction = (position - nak_index * nak_span) / nak_span
    start_lord = NAKSHATRA_LORDS[nak_index]
    lord_idx = DASHA_ORDER.index(start_lord)
    offset = 0.0
    sub_lord = None
    sub_fraction = None
    for n in range(9):
        lord = DASHA_ORDER[(lord_idx + n) % 9]
        part = DASHA_YEARS[lord] / 120.0
        if fraction < offset + part or n == 8:
            sub_lord = lord
            sub_fraction = (fraction - offset) / part
            break
        offset += part
    return {
        "nakshatra": NAKSHATRAS[nak_index],
        "star_lord": start_lord,
        "sub_lord": sub_lord,
        "sub_sub_lord_progress": round(sub_fraction or 0.0, 6),
        "method": "Each 13°20′ nakshatra is divided into nine Vimshottari-proportional segments.",
    }


def jaimini_chara_karakas(positions: dict, include_rahu: bool = True) -> list[dict]:
    candidates = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    if include_rahu:
        candidates.append("Rahu")
    ranked = []
    for planet in candidates:
        if planet not in positions:
            continue
        degree = sign_degree(positions[planet]["sidereal_longitude"])
        value = 30.0 - degree if planet == "Rahu" else degree
        ranked.append((value, planet, degree))
    ranked.sort(reverse=True)
    role_names = ["Atmakaraka", "Amatyakaraka", "Bhratrukaraka", "Matrukaraka", "Putrakaraka", "Gnatikaraka", "Darakaraka", "Pitrukaraka"]
    return [{"karaka": role_names[i], "planet": planet, "degree_in_sign": round(degree, 5), "ranking_value": round(value, 5)} for i, (value, planet, degree) in enumerate(ranked)]


def jaimini_rashi_drishti() -> list[dict]:
    aspects = []
    # 0-based signs: movable (0,3,6,9), fixed (1,4,7,10), dual (2,5,8,11).
    movable = {0, 3, 6, 9}
    fixed = {1, 4, 7, 10}
    dual = {2, 5, 8, 11}
    for source in range(12):
        if source in movable:
            targets = [x for x in fixed if x not in {(source - 1) % 12, (source + 1) % 12}]
        elif source in fixed:
            targets = [x for x in movable if x not in {(source - 1) % 12, (source + 1) % 12}]
        else:
            targets = list(dual - {source})
        for target in sorted(targets):
            aspects.append({"from_sign": SIGNS[source], "to_sign": SIGNS[target]})
    return aspects


def detect_yogas_and_doshas(positions: dict, houses: dict, house_map: dict) -> list[dict]:
    found = []
    longitudes = {k: v["sidereal_longitude"] for k, v in positions.items()}
    def add(code, name, status, evidence, caveat):
        found.append({"code": code, "name": name, "status": status, "evidence": evidence, "caveat": caveat})

    # Gajakesari: Jupiter in a kendra from Moon.
    moon_house = house_map.get("Moon")
    jupiter_house = house_map.get("Jupiter")
    if moon_house and jupiter_house:
        distance = (jupiter_house - moon_house) % 12
        if distance in (0, 3, 6, 9):
            add("gajakesari", "Gajakesari Yoga", "rule_match", [f"Jupiter is in a kendra from Moon (house distance {distance + 1})."], "Traditional schools add strength, dignity and affliction conditions; this is a structural match only.")

    if "Sun" in longitudes and "Mercury" in longitudes:
        orb = angular_difference(longitudes["Sun"], longitudes["Mercury"])
        if orb <= 10:
            add("budhaditya", "Budhaditya Yoga", "rule_match", [f"Sun–Mercury separation is {orb:.2f}° (≤10° rule)."], "Combustion and house context materially change interpretation.")

    for planet, code, yoga_name in [("Mars", "ruchaka", "Ruchaka Yoga"), ("Mercury", "bhadra", "Bhadra Yoga"), ("Jupiter", "hamsa", "Hamsa Yoga"), ("Venus", "malavya", "Malavya Yoga"), ("Saturn", "shasha", "Shasha Yoga")]:
        if planet in positions:
            dign = planetary_dignities({planet: positions[planet]})[planet]["dignity"]
            house = house_map.get(planet)
            if dign in ("own_sign", "exalted") and house in (1, 4, 7, 10):
                add(code, yoga_name, "rule_match", [f"{planet} is {dign} and occupies kendra house {house}."], "Traditional strength, combustion, retrogression and divisional-chart conditions are not fully scored in this release.")

    mars_house = house_map.get("Mars")
    if mars_house in (1, 2, 4, 7, 8, 12):
        add("manglik", "Manglik / Kuja Dosha", "tradition_sensitive_match", [f"Mars occupies house {mars_house}; selected rule uses houses 1, 2, 4, 7, 8 and 12."], "House lists, exceptions and cancellation rules differ substantially by school; no relationship outcome is inferred.")

    for luminary in ("Sun", "Moon"):
        if luminary in longitudes:
            nearest = min(("Rahu", "Ketu"), key=lambda node: angular_difference(longitudes[luminary], longitudes[node]))
            orb = angular_difference(longitudes[luminary], longitudes[nearest])
            if orb <= 8:
                add("grahan", "Grahan Yoga / eclipse proximity", "rule_match", [f"{luminary} is {orb:.2f}° from {nearest}."], "Orb thresholds vary; this module reports angular proximity rather than a guaranteed effect.")

    if "Jupiter" in longitudes:
        for node in ("Rahu", "Ketu"):
            orb = angular_difference(longitudes["Jupiter"], longitudes[node])
            if orb <= 8:
                add("guru_chandal", "Guru Chandal Yoga", "tradition_sensitive_match", [f"Jupiter is {orb:.2f}° from {node}."], "Different schools define the conjunction and cancellation differently.")

    # Kemadruma structural check: no classical planets in 2nd/12th from Moon and no planet in Moon kendras.
    moon_sign = sign_index(longitudes["Moon"])
    classical = [p for p in ("Sun", "Mars", "Mercury", "Jupiter", "Venus", "Saturn") if p in longitudes]
    adjacent = [p for p in classical if (sign_index(longitudes[p]) - moon_sign) % 12 in (1, 11)]
    kendras = [p for p in classical if (sign_index(longitudes[p]) - moon_sign) % 12 in (0, 3, 6, 9)]
    if not adjacent and not kendras:
        add("kemadruma", "Kemadruma Yoga", "rule_match", ["No classical planet is in the 2nd/12th from Moon or in a kendra from Moon by sign."], "There are additional cancellation conditions; this is not a final dosha verdict.")

    return found
