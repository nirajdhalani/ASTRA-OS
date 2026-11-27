from app.astro.houses import calculate_houses, house_for_longitude


def test_whole_sign_cusps_start_at_ascendant_sign():
    houses = calculate_houses(120, 20, 23.4, "whole_sign", sidereal_offset=24)
    assert len(houses["cusps"]) == 12
    assert houses["cusps"][1] == (houses["cusps"][0] + 30) % 360
    assert house_for_longitude(houses["cusps"][0] + 2, houses["cusps"], "whole_sign") == 1
    assert house_for_longitude(houses["cusps"][0] + 31, houses["cusps"], "whole_sign") == 2


def test_equal_house_cusps_are_30_degrees_apart():
    houses = calculate_houses(180, 10, 23.4, "equal")
    for i in range(11):
        assert abs((houses["cusps"][i+1] - houses["cusps"][i]) % 360 - 30) < 1e-8


def test_placidus_refuses_extreme_latitude():
    try:
        calculate_houses(120, 75, 23.4, "placidus")
    except ValueError as exc:
        assert "latitude" in str(exc)
    else:
        raise AssertionError("Expected Placidus polar-region guard")


def test_equal_house_cusps_apply_sidereal_offset():
    tropical = calculate_houses(180, 10, 23.4, "equal", sidereal_offset=0)
    sidereal = calculate_houses(180, 10, 23.4, "equal", sidereal_offset=24)
    assert abs((tropical["cusps"][0] - sidereal["cusps"][0]) % 360 - 24) < 1e-8


def test_placidus_cusps_are_distinct_and_cyclically_ordered_at_mid_latitude():
    for latitude in (0, 21.5222, 45, 60, 65):
        for lst in range(0, 360, 15):
            houses = calculate_houses(lst, latitude, 23.4, "placidus")
            cusps = houses["cusps"]
            spans = [((cusps[(i + 1) % 12] - cusps[i]) % 360) for i in range(12)]
            assert all(span > 0.1 for span in spans), (lst, cusps, spans)
            assert all(abs(((cusps[i + 6] - cusps[i]) % 360) - 180) < 1e-4 for i in range(6))
