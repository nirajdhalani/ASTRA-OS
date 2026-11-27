import json
from datetime import datetime, timezone
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..config import settings
from ..database import get_db
from ..models import BirthProfile, User
from ..schemas import BirthInput, ChartSummary
from ..security import current_user
from ..astro.chart_service import build_chart, ChartCalculationError
from ..astro.ephemeris import SkyfieldProvider, EphemerisUnavailable
from ..astro.time_utils import BirthTimeError, resolve_local_birth_time

router = APIRouter(prefix="/api/charts", tags=["birth charts"])


@lru_cache(maxsize=1)
def _provider():
    return SkyfieldProvider(settings.ephemeris_dir, settings.ephemeris_file)


def _resolve_location(payload: BirthInput):
    if payload.latitude is not None and payload.longitude is not None:
        latitude, longitude = payload.latitude, payload.longitude
        place = payload.place
    else:
        from .geo import _lookup
        results = _lookup(payload.place)
        if not results:
            raise HTTPException(status_code=422, detail="Birthplace could not be geocoded. Pick a search result or enter coordinates.")
        latitude, longitude, place = results[0]["latitude"], results[0]["longitude"], results[0]["label"]
    timezone_name = payload.timezone_name
    if not timezone_name:
        try:
            from timezonefinder import TimezoneFinder
            timezone_name = TimezoneFinder(in_memory=True).timezone_at(lat=latitude, lng=longitude)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Timezone resolver is not available. Supply an IANA timezone name.") from exc
    if not timezone_name:
        raise HTTPException(status_code=422, detail="No timezone found for this birthplace. Enter its IANA timezone name.")
    return latitude, longitude, place, timezone_name


def _calculate(payload: BirthInput):
    latitude, longitude, place, timezone_name = _resolve_location(payload)
    local_naive = datetime.combine(payload.birth_date, payload.birth_time.replace(tzinfo=None))
    try:
        birth_utc = resolve_local_birth_time(local_naive, timezone_name, payload.fold)
    except BirthTimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    request_data = payload.model_dump(mode="json")
    request_data.update({"latitude": latitude, "longitude": longitude, "place": place, "timezone_name": timezone_name})
    try:
        chart = build_chart(request_data, birth_utc, _provider())
    except EphemerisUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ChartCalculationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return chart, request_data


@router.post("/preview")
def preview_chart(payload: BirthInput, user: User = Depends(current_user)):
    chart, _ = _calculate(payload)
    return chart


@router.post("", response_model=ChartSummary, status_code=201)
def create_chart(payload: BirthInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.plan != "pro":
        saved_count = db.scalar(select(func.count(BirthProfile.id)).where(BirthProfile.owner_id == user.id)) or 0
        if saved_count >= settings.free_chart_limit:
            raise HTTPException(
                status_code=402,
                detail=f"Free plan limit reached ({settings.free_chart_limit} saved charts). Upgrade to ASTRA Pro to save more charts.",
            )
    chart, request_data = _calculate(payload)
    profile = BirthProfile(
        owner_id=user.id,
        label=payload.label,
        birth_date=payload.birth_date.isoformat(),
        birth_time=payload.birth_time.strftime("%H:%M"),
        place=request_data["place"],
        latitude=request_data["latitude"],
        longitude=request_data["longitude"],
        timezone_name=request_data["timezone_name"],
        locale=payload.locale,
        chart_system=payload.chart_system,
        ayanamsa=payload.ayanamsa,
        house_system=payload.house_system or ("placidus" if payload.chart_system in ("western", "kp") else "whole_sign"),
        chart_json=json.dumps(chart, ensure_ascii=False),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return ChartSummary(id=profile.id, label=profile.label, birth_date=profile.birth_date, birth_time=profile.birth_time, place=profile.place, chart_system=profile.chart_system, created_at=profile.created_at.isoformat())


@router.get("")
def list_charts(db: Session = Depends(get_db), user: User = Depends(current_user)):
    profiles = db.scalars(select(BirthProfile).where(BirthProfile.owner_id == user.id).order_by(BirthProfile.created_at.desc())).all()
    return [{"id": p.id, "label": p.label, "birth_date": p.birth_date, "birth_time": p.birth_time, "place": p.place, "chart_system": p.chart_system, "created_at": p.created_at.isoformat()} for p in profiles]


@router.get("/{profile_id}")
def get_chart(profile_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    profile = db.scalar(select(BirthProfile).where(BirthProfile.id == profile_id, BirthProfile.owner_id == user.id))
    if not profile:
        raise HTTPException(status_code=404, detail="Birth chart not found")
    chart = json.loads(profile.chart_json)
    if chart.get("vimshottari_dasha") and chart.get("planetary_positions", {}).get("Moon", {}).get("sidereal_longitude") is not None:
        from ..astro.dasha import vimshottari_dasha
        birth_utc = datetime.fromisoformat(chart["birth"]["utc_datetime"])
        chart["vimshottari_dasha"] = vimshottari_dasha(
            chart["planetary_positions"]["Moon"]["sidereal_longitude"],
            birth_utc,
            now_utc=datetime.now(timezone.utc),
            cycles=4,
        )
        chart["birth"]["analysis_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    return chart


@router.delete("/{profile_id}", status_code=204)
def delete_chart(profile_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    profile = db.scalar(select(BirthProfile).where(BirthProfile.id == profile_id, BirthProfile.owner_id == user.id))
    if not profile:
        raise HTTPException(status_code=404, detail="Birth chart not found")
    db.delete(profile)
    db.commit()
    return None
