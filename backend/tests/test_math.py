from datetime import datetime, timezone
from app.astro.math_utils import julian_day, norm360, sign_index, sign_degree, nakshatra_data, ayanamsa_value
from app.astro.dasha import vimshottari_dasha


def test_julian_day_j2000_epoch():
    assert julian_day(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)) == 2451545.0


def test_longitude_normalization_and_sign_boundary():
    assert norm360(361.25) == 1.25
    assert sign_index(29.999) == 0
    assert sign_index(30.0) == 1
    assert sign_degree(43.5) == 13.5


def test_nakshatra_boundaries_and_pada():
    first = nakshatra_data(0)
    assert first["name"] == "Ashwini" and first["lord"] == "Ketu" and first["pada"] == 1
    next_nak = nakshatra_data(13 + 20/60)
    assert next_nak["name"] == "Bharani"
    assert nakshatra_data(360)["name"] == "Ashwini"


def test_ayanamsa_known_range_and_systems():
    jd = julian_day(datetime(2000, 1, 1, 12, tzinfo=timezone.utc))
    lahiri = ayanamsa_value("lahiri", jd)
    kp = ayanamsa_value("kp", jd)
    assert 23.7 < lahiri < 24.0
    assert kp < lahiri
    assert abs(ayanamsa_value("tropical", jd)) < 1e-12


def test_vimshottari_cycle_is_120_years():
    birth = datetime(1998, 6, 9, 9, 45, tzinfo=timezone.utc)
    report = vimshottari_dasha(42.0, birth)
    assert report["sequence_years"] == 120
    assert round(sum([7,20,6,10,7,18,16,19,17])) == 120
    assert report["periods"]
    assert report["birth_balance_years"] > 0
