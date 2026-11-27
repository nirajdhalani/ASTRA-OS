from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class BirthTimeError(ValueError):
    pass


def resolve_local_birth_time(local_naive: datetime, timezone_name: str, fold: int | None = None) -> datetime:
    """Resolve wall clock time to UTC; reject DST gaps and require fold for overlaps."""
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise BirthTimeError(f"Unknown IANA timezone: {timezone_name}") from exc

    valid: list[tuple[int, datetime]] = []
    for candidate_fold in (0, 1):
        local_aware = local_naive.replace(tzinfo=zone, fold=candidate_fold)
        utc_value = local_aware.astimezone(timezone.utc)
        round_trip = utc_value.astimezone(zone).replace(tzinfo=None)
        if round_trip == local_naive:
            valid.append((candidate_fold, utc_value))

    unique = {item[1] for item in valid}
    if not unique:
        raise BirthTimeError("This local birth time does not exist because the clock moved forward. Confirm the recorded time or use another documented time.")
    if len(unique) > 1:
        if fold is None:
            raise BirthTimeError("This local birth time occurs twice because of a clock change. Select the earlier or later occurrence (fold 0 or 1).")
        for candidate_fold, utc_value in valid:
            if candidate_fold == fold:
                return utc_value
        raise BirthTimeError("Selected fold is invalid for this local time.")
    return next(iter(unique))
