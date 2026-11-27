import pytest
from pydantic import ValidationError
from app.schemas import BirthInput


def base_payload():
    return {
        "birth_date": "1998-06-09", "birth_time": "15:15", "place": "Junagadh, Gujarat, India",
        "latitude": 21.5222, "longitude": 70.4579, "timezone_name": "Asia/Kolkata",
    }


def test_western_schema_forces_tropical_zodiac():
    payload = BirthInput(**{**base_payload(), "chart_system": "western", "ayanamsa": "lahiri"})
    assert payload.ayanamsa == "tropical"


def test_kp_schema_forces_kp_ayanamsa():
    payload = BirthInput(**{**base_payload(), "chart_system": "kp", "ayanamsa": "lahiri"})
    assert payload.ayanamsa == "kp"


def test_sidereal_system_rejects_tropical_zodiac():
    with pytest.raises(ValidationError):
        BirthInput(**{**base_payload(), "chart_system": "vedic", "ayanamsa": "tropical"})
