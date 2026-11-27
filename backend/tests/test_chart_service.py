from datetime import datetime, timezone
from app.astro.chart_service import build_chart


class FakeProvider:
    def positions(self, dt):
        vals = {"Sun": 75.2, "Moon": 100.4, "Mercury": 82.0, "Venus": 120.0, "Mars": 200.0, "Jupiter": 110.0, "Saturn": 280.0, "Uranus": 20.0, "Neptune": 350.0, "Pluto": 245.0}
        return {name: {"tropical_longitude": lon, "speed_degrees_per_day": 0.2 if name not in ("Saturn",) else -0.03} for name, lon in vals.items()}
    def gast_degrees(self, dt):
        return 180.0


def test_vedic_chart_contains_core_outputs():
    payload = {
        "birth_date": "1998-06-09", "birth_time": "15:15:00", "place": "Junagadh, Gujarat, India",
        "latitude": 21.5222, "longitude": 70.4579, "timezone_name": "Asia/Kolkata",
        "chart_system": "vedic", "ayanamsa": "lahiri", "house_system": "whole_sign", "locale": "en",
    }
    dt = datetime(1998, 6, 9, 9, 45, tzinfo=timezone.utc)
    chart = build_chart(payload, dt, FakeProvider(), now_utc=datetime(2026, 11, 27, tzinfo=timezone.utc))
    assert chart["configuration"]["chart_system"] == "vedic"
    assert len(chart["houses"]["cusps"]) == 12
    assert "D1" in chart["divisional_charts"] and "D9" in chart["divisional_charts"] and "D60" in chart["divisional_charts"]
    assert "Rahu" in chart["planetary_positions"] and "Ketu" in chart["planetary_positions"]
    assert len(chart["life_domains"]) == 18
    assert chart["vimshottari_dasha"]["periods"]
    assert chart["quality"]["calculation_status"] == "calculated"
    assert chart["birth"]["analysis_timestamp_utc"].startswith("2026-11-27")
    assert chart["vimshottari_dasha"]["now_utc"].startswith("2026-11-27")
    assert chart["vimshottari_dasha"]["current_mahadasha"] is not None
    assert chart["vimshottari_dasha"]["current_antardasha"] is not None


def test_western_chart_uses_tropical_and_omits_vedic_outputs():
    payload = {
        "birth_date": "1998-06-09", "birth_time": "15:15:00", "place": "Junagadh, Gujarat, India",
        "latitude": 21.5222, "longitude": 70.4579, "timezone_name": "Asia/Kolkata",
        "chart_system": "western", "ayanamsa": "lahiri", "house_system": "equal", "locale": "en",
    }
    dt = datetime(1998, 6, 9, 9, 45, tzinfo=timezone.utc)
    chart = build_chart(payload, dt, FakeProvider())
    assert chart["configuration"]["ayanamsa"] == "tropical"
    assert chart["configuration"]["ayanamsa_degrees"] == 0
    assert chart["divisional_charts"] == {}
    assert chart["vimshottari_dasha"] is None
    assert chart["aspects"]["western"]


def test_western_chart_does_not_label_tropical_longitudes_as_nakshatra_or_panchang():
    payload = {
        "birth_date": "1998-06-09", "birth_time": "15:15:00", "place": "Junagadh, Gujarat, India",
        "latitude": 21.5222, "longitude": 70.4579, "timezone_name": "Asia/Kolkata",
        "chart_system": "western", "ayanamsa": "tropical", "house_system": "equal", "locale": "en",
    }
    dt = datetime(1998, 6, 9, 9, 45, tzinfo=timezone.utc)
    chart = build_chart(payload, dt, FakeProvider())
    assert chart["panchang"] is None
    assert all(p["nakshatra"] is None for p in chart["planetary_positions"].values())


def test_kp_and_jaimini_engines_return_system_specific_outputs():
    base = {
        "birth_date": "1998-06-09", "birth_time": "15:15:00", "place": "Junagadh, Gujarat, India",
        "latitude": 21.5222, "longitude": 70.4579, "timezone_name": "Asia/Kolkata",
        "ayanamsa": "lahiri", "house_system": "whole_sign", "locale": "en",
    }
    dt = datetime(1998, 6, 9, 9, 45, tzinfo=timezone.utc)
    kp_payload = {**base, "chart_system": "kp"}
    kp_payload.pop("house_system")
    kp_chart = build_chart(kp_payload, dt, FakeProvider())
    assert kp_chart["configuration"]["ayanamsa"] == "kp"
    assert kp_chart["houses"]["system"] == "placidus"
    assert kp_chart["kp_analysis"]["planetary_sub_lords"]["Moon"]["sub_lord"]
    assert len(kp_chart["kp_analysis"]["cusp_sub_lords"]) == 12
    jaimini_chart = build_chart({**base, "chart_system": "jaimini"}, dt, FakeProvider())
    assert jaimini_chart["jaimini_analysis"]["chara_karakas_8"]
    assert jaimini_chart["jaimini_analysis"]["rashi_drishti"]
