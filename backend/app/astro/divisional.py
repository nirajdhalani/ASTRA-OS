from .math_utils import norm360, sign_index, sign_degree


def _varga_sign(sign: int, part: int, number: int) -> int:
    odd = sign % 2 == 0  # Aries, Gemini... are odd signs (zero-based even index)
    if number == 1:
        return sign
    if number == 2:  # Hora: Sun/Leo and Moon/Cancer
        if odd:
            return 4 if part == 0 else 3
        return 3 if part == 0 else 4
    if number == 3:
        return (sign + part * 4) % 12
    if number == 4:
        return (sign + part * 3) % 12
    if number == 7:
        return (sign + part + (0 if odd else 6)) % 12
    if number == 9:
        modality_start = sign if sign % 3 == 0 else (sign + 8) % 12 if sign % 3 == 1 else (sign + 4) % 12
        return (modality_start + part) % 12
    if number == 10:
        return (sign + part + (0 if odd else 8)) % 12
    if number == 12:
        return (sign + part) % 12
    if number == 16:
        start = 0 if sign % 3 == 0 else 4 if sign % 3 == 1 else 8
        return (start + part) % 12
    if number == 20:
        start = 0 if sign % 3 == 0 else 8 if sign % 3 == 1 else 4
        return (start + part) % 12
    if number == 24:
        start = 4 if odd else 3
        return (start + part) % 12
    if number == 27:
        start_by_element = {0: 0, 1: 3, 2: 6, 3: 9}
        return (start_by_element[sign % 4] + part) % 12
    if number == 30:
        # Classical five unequal portions; mapping differs for odd/even signs.
        odd_parts = [(5, 0), (5, 10), (8, 8), (7, 2), (5, 6)]  # Aries, Aquarius, Sagittarius, Gemini, Libra
        even_parts = [(5, 1), (7, 5), (8, 11), (5, 9), (5, 7)]  # Taurus, Virgo, Pisces, Capricorn, Scorpio
        portions = odd_parts if odd else even_parts
        cursor = 0.0
        degree = part / 30.0 * 30.0
        for width, target in portions:
            if degree < cursor + width:
                return target
            cursor += width
        return portions[-1][1]
    if number == 40:
        return (0 if odd else 6) + part % 12
    if number == 45:
        start = 0 if sign % 3 == 0 else 4 if sign % 3 == 1 else 8
        return (start + part) % 12
    if number == 60:
        return (sign + part) % 12
    return sign


def divisional_charts(positions: dict[str, dict], ascendant: float, vargas: list[int]) -> dict:
    points = {name: data["sidereal_longitude"] for name, data in positions.items()}
    points["Ascendant"] = ascendant
    output = {}
    for number in vargas:
        entries = {}
        for name, longitude in points.items():
            sign = sign_index(longitude)
            deg = sign_degree(longitude)
            divisions = 30.0 / number if number not in (30,) else 1.0
            if number == 30:
                # Determine the unequal D30 segment and return its ruler sign.
                odd = sign % 2 == 0
                portions = [(5, 0), (5, 10), (8, 8), (7, 2), (5, 6)] if odd else [(5, 1), (7, 5), (8, 11), (5, 9), (5, 7)]
                cursor = 0.0
                mapped = sign
                for width, target in portions:
                    if deg < cursor + width:
                        mapped = target
                        break
                    cursor += width
            else:
                part = min(number - 1, int(deg / divisions))
                mapped = _varga_sign(sign, part, number)
            fraction = (deg % divisions) / divisions * 30.0
            entries[name] = {"sign_index": mapped, "degree": round(fraction, 5), "longitude": round(mapped * 30.0 + fraction, 5)}
        output[f"D{number}"] = entries
    return output
