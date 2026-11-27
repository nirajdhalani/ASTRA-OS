from .constants import NAKSHATRAS
from .math_utils import norm360, nakshatra_data

TITHIS = ["Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima"]
YOGAS = ["Vishkumbha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma", "Dhriti", "Shoola", "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti"]
MOVING_KARANAS = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]


def calculate_panchang(sun_longitude: float, moon_longitude: float, birth_weekday: int) -> dict:
    elongation = norm360(moon_longitude - sun_longitude)
    tithi_number = min(30, int(elongation / 12.0) + 1)
    half = "Shukla" if tithi_number <= 15 else "Krishna"
    tithi_name = TITHIS[tithi_number - 1] if tithi_number <= 15 else ("Amavasya" if tithi_number == 30 else TITHIS[tithi_number - 16])
    yoga_index = int(norm360(sun_longitude + moon_longitude) / (360.0 / 27.0)) % 27
    karana_index = min(59, int(elongation / 6.0))
    if karana_index == 0:
        karana_name = "Kimstughna"
    elif karana_index <= 56:
        karana_name = MOVING_KARANAS[(karana_index - 1) % 7]
    else:
        karana_name = ["Shakuni", "Chatushpada", "Naga"][karana_index - 57]
    weekday = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][birth_weekday]
    return {
        "weekday": weekday,
        "tithi": {"number": tithi_number, "half": half, "name": tithi_name},
        "nakshatra": nakshatra_data(moon_longitude),
        "yoga": YOGAS[yoga_index],
        "karana": karana_name,
        "elongation_degrees": round(elongation, 6),
    }
