from datetime import datetime, timedelta, timezone
from .constants import DASHA_ORDER, DASHA_YEARS
from .math_utils import nakshatra_data, norm360

YEAR_DAYS = 365.2425


def _add_years(start: datetime, years: float) -> datetime:
    return start + timedelta(days=years * YEAR_DAYS)


def vimshottari_dasha(moon_sidereal_longitude: float, birth_utc: datetime, now_utc: datetime | None = None, cycles: int = 2) -> dict:
    moon = norm360(moon_sidereal_longitude)
    span = 360.0 / 27.0
    nak = nakshatra_data(moon)
    lord_index = DASHA_ORDER.index(nak["lord"])
    elapsed_fraction = (moon % span) / span
    first_lord = DASHA_ORDER[lord_index]
    first_total = DASHA_YEARS[first_lord]
    first_elapsed_years = first_total * elapsed_fraction
    first_balance = first_total - first_elapsed_years
    first_start = birth_utc - timedelta(days=first_elapsed_years * YEAR_DAYS)

    current = birth_utc if now_utc is None else now_utc.astimezone(timezone.utc)
    periods = []
    start = first_start
    sequence_count = cycles * 9
    for offset in range(sequence_count):
        current_index = (lord_index + offset) % 9
        lord = DASHA_ORDER[current_index]
        years = DASHA_YEARS[lord]
        end = _add_years(start, years)
        if offset == 0:
            effective_start = birth_utc
        else:
            effective_start = start
        if end >= birth_utc:
            antardashas = []
            sub_start = start
            for sub_offset in range(9):
                sub_lord = DASHA_ORDER[(current_index + sub_offset) % 9]
                sub_years = years * DASHA_YEARS[sub_lord] / 120.0
                sub_end = _add_years(sub_start, sub_years)
                antardashas.append({
                    "lord": sub_lord,
                    "start": sub_start.isoformat(),
                    "end": sub_end.isoformat(),
                    "active_at_birth": sub_start <= birth_utc < sub_end,
                    "active_now": sub_start <= current < sub_end,
                })
                sub_start = sub_end
            periods.append({
                "lord": lord,
                "nominal_years": years,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "effective_start": effective_start.isoformat(),
                "balance_at_birth_years": round(first_balance, 6) if offset == 0 else None,
                "active_at_birth": start <= birth_utc < end,
                "active_now": start <= current < end,
                "antardashas": antardashas,
            })
        start = end
    active = next((p for p in periods if p["active_now"]), None)
    active_sub = None
    if active:
        active_sub = next((a for a in active["antardashas"] if a["active_now"]), None)
    return {
        "system": "Vimshottari",
        "nakshatra": nak,
        "sequence_years": 120,
        "year_length_days": YEAR_DAYS,
        "birth_balance_years": round(first_balance, 6),
        "periods": periods,
        "current_mahadasha": active,
        "current_antardasha": active_sub,
        "now_utc": current.isoformat(),
        "method_note": "Calendar boundaries use a 365.2425-day dasha year; other software may differ by days if it uses a different year convention.",
    }
