from .constants import SIGNS
from .math_utils import sign_index

DOMAIN_CONFIG = {
    "personality": {"houses": [1], "en": "Personality & identity", "hi": "व्यक्तित्व और पहचान", "gu": "વ્યક્તિત્વ અને ઓળખ"},
    "career": {"houses": [6, 10, 11], "en": "Career & profession", "hi": "करियर और पेशा", "gu": "કારકિર્દી અને વ્યવસાય"},
    "wealth": {"houses": [2, 5, 9, 11], "en": "Wealth & finances", "hi": "धन और वित्त", "gu": "ધન અને નાણાં"},
    "fame": {"houses": [1, 5, 9, 10, 11], "en": "Fame & public standing", "hi": "प्रसिद्धि और सामाजिक प्रतिष्ठा", "gu": "પ્રસિદ્ધિ અને સામાજિક પ્રતિષ્ઠા"},
    "relationships": {"houses": [5, 7, 8], "en": "Love & relationships", "hi": "प्रेम और रिश्ते", "gu": "પ્રેમ અને સંબંધો"},
    "marriage": {"houses": [2, 7, 8, 12], "en": "Marriage & partnership", "hi": "विवाह और साझेदारी", "gu": "લગ્ન અને ભાગીદારી"},
    "health": {"houses": [1, 6, 8, 12], "en": "Health & wellbeing", "hi": "स्वास्थ्य और कल्याण", "gu": "આરોગ્ય અને સુખાકારી"},
    "legal": {"houses": [6, 7, 8, 9, 12], "en": "Legal matters & disputes", "hi": "कानूनी मामले और विवाद", "gu": "કાનૂની બાબતો અને વિવાદો"},
    "family": {"houses": [2, 4, 9], "en": "Family & parents", "hi": "परिवार और माता-पिता", "gu": "પરિવાર અને માતા-પિતા"},
    "children": {"houses": [5, 9], "en": "Children & parenthood", "hi": "संतान और माता-पितृत्व", "gu": "સંતાન અને માતાપિતૃત્વ"},
    "education": {"houses": [4, 5, 9], "en": "Education & learning", "hi": "शिक्षा और अध्ययन", "gu": "શિક્ષણ અને અભ્યાસ"},
    "property": {"houses": [2, 4, 11], "en": "Property & assets", "hi": "संपत्ति और परिसंपत्तियां", "gu": "મિલકત અને સંપત્તિ"},
    "foreign": {"houses": [7, 9, 12], "en": "Foreign travel & relocation", "hi": "विदेश यात्रा और स्थानांतरण", "gu": "વિદેશ પ્રવાસ અને સ્થળાંતર"},
    "spirituality": {"houses": [8, 9, 12], "en": "Spirituality & inner life", "hi": "आध्यात्मिकता और आंतरिक जीवन", "gu": "આધ્યાત્મિકતા અને આંતરિક જીવન"},
    "competition": {"houses": [3, 6, 10, 11], "en": "Competition & opposition", "hi": "प्रतिस्पर्धा और विरोध", "gu": "સ્પર્ધા અને વિરોધ"},
    "business": {"houses": [2, 7, 10, 11], "en": "Business & entrepreneurship", "hi": "व्यवसाय और उद्यमिता", "gu": "વ્યવસાય અને ઉદ્યોગસાહસિકતા"},
    "creativity": {"houses": [3, 5], "en": "Creativity & communication", "hi": "रचनात्मकता और संचार", "gu": "સર્જનાત્મકતા અને સંચાર"},
    "social": {"houses": [3, 10, 11], "en": "Friends & social networks", "hi": "मित्र और सामाजिक नेटवर्क", "gu": "મિત્રો અને સામાજિક નેટવર્ક"},
}

BENEFIC_CUES = {"Jupiter", "Venus"}
CHALLENGE_CUES = {"Saturn", "Mars", "Rahu", "Ketu"}


def build_domain_reports(positions: dict, houses: dict, house_map: dict, locale: str = "en") -> list[dict]:
    # House lord rulership is a declared classical Parashari mapping, not a probability model.
    sign_lords = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
    output = []
    for code, config in DOMAIN_CONFIG.items():
        house_facts = []
        supportive = []
        challenging = []
        for house in config["houses"]:
            cusp = houses["cusps"][house - 1]
            sign = sign_index(cusp)
            lord = sign_lords[sign]
            occupants = [p for p, h in house_map.items() if h == house]
            lord_house = house_map.get(lord)
            fact = {"house": house, "sign": SIGNS[sign], "lord": lord, "lord_house": lord_house, "occupants": occupants}
            house_facts.append(fact)
            for planet in occupants:
                if planet in BENEFIC_CUES:
                    supportive.append({"type": "occupant", "planet": planet, "house": house, "sign": SIGNS[sign]})
                elif planet in CHALLENGE_CUES:
                    challenging.append({"type": "occupant", "planet": planet, "house": house, "sign": SIGNS[sign]})
            if lord in positions:
                dignity = positions[lord].get("dignity", "neutral")
                if dignity in ("own_sign", "exalted"):
                    supportive.append({"type": "house_lord_dignity", "planet": lord, "house": house, "dignity": dignity})
                elif dignity == "debilitated":
                    challenging.append({"type": "house_lord_dignity", "planet": lord, "house": house, "dignity": dignity})
        output.append({
            "code": code,
            "title": config.get(locale, config["en"]),
            "houses_considered": config["houses"],
            "house_evidence": house_facts,
            "supporting_factors": supportive,
            "challenging_factors": challenging,
            "interpretation": {
                "en": "This section lists the traditional chart factors used for this topic. Read supporting and challenging factors together; neither set establishes that a real-world event will occur.",
                "hi": "यह अनुभाग इस विषय से जुड़े पारंपरिक ज्योतिषीय कारक दिखाता है। सहायक और चुनौतीपूर्ण कारकों को साथ पढ़ें; इनमें से कोई भी वास्तविक घटना की गारंटी नहीं देता।",
                "gu": "આ વિભાગ આ વિષય માટેના પરંપરાગત જ્યોતિષીય પરિબળો દર્શાવે છે. સહાયક અને પડકારજનક પરિબળો સાથે વાંચો; કોઈ પણ વાસ્તવિક ઘટના થવાની ખાતરી આપતું નથી.",
            }[locale],
        })
    return output
