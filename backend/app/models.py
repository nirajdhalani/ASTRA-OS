from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    locale: Mapped[str] = mapped_column(String(8), default="en")
    plan: Mapped[str] = mapped_column(String(24), default="free")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    profiles: Mapped[list["BirthProfile"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class BirthProfile(Base):
    __tablename__ = "birth_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(120), default="My birth chart")
    birth_date: Mapped[str] = mapped_column(String(10))
    birth_time: Mapped[str] = mapped_column(String(5))
    place: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float] = mapped_column()
    longitude: Mapped[float] = mapped_column()
    timezone_name: Mapped[str] = mapped_column(String(80))
    locale: Mapped[str] = mapped_column(String(8), default="en")
    chart_system: Mapped[str] = mapped_column(String(16), default="vedic")
    ayanamsa: Mapped[str] = mapped_column(String(24), default="lahiri")
    house_system: Mapped[str] = mapped_column(String(24), default="whole_sign")
    chart_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    owner: Mapped[User] = relationship(back_populates="profiles")
