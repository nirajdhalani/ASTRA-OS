from datetime import date, time
from typing import Literal
from pydantic import BaseModel, Field, model_validator

Locale = Literal["en", "hi", "gu"]
System = Literal["vedic", "western", "kp", "jaimini"]
Ayanamsa = Literal["lahiri", "kp", "raman", "fagan_bradley", "tropical"]
HouseSystem = Literal["whole_sign", "equal", "placidus"]


class RegisterInput(BaseModel):
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=320)
    password: str = Field(min_length=10, max_length=128)
    locale: Locale = "en"


class LoginInput(BaseModel):
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=320)
    password: str


class UserOutput(BaseModel):
    id: int
    email: str
    locale: str
    plan: str


class AuthOutput(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOutput


class BirthInput(BaseModel):
    label: str = Field(default="My birth chart", max_length=120)
    birth_date: date
    birth_time: time
    place: str = Field(min_length=2, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone_name: str | None = Field(default=None, min_length=3, max_length=80)
    fold: Literal[0, 1] | None = None
    locale: Locale = "en"
    chart_system: System = "vedic"
    ayanamsa: Ayanamsa = "lahiri"
    house_system: HouseSystem | None = None

    @model_validator(mode="after")
    def coordinates_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be supplied together")
        if self.chart_system == "western":
            self.ayanamsa = "tropical"
        elif self.ayanamsa == "tropical":
            raise ValueError("Tropical zodiac is only valid for Western charts; choose a sidereal ayanamsa.")
        if self.chart_system == "kp":
            self.ayanamsa = "kp"
        return self


class ChartSummary(BaseModel):
    id: int
    label: str
    birth_date: str
    birth_time: str
    place: str
    chart_system: str
    created_at: str
