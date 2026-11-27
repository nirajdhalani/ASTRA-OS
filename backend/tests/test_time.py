from datetime import datetime, timezone
import pytest
from app.astro.time_utils import BirthTimeError, resolve_local_birth_time


def test_india_birth_time_conversion():
    local = datetime(1998, 6, 9, 15, 15)
    utc = resolve_local_birth_time(local, "Asia/Kolkata")
    assert utc == datetime(1998, 6, 9, 9, 45, tzinfo=timezone.utc)


def test_dst_gap_is_rejected():
    with pytest.raises(BirthTimeError, match="does not exist"):
        resolve_local_birth_time(datetime(2024, 3, 10, 2, 30), "America/New_York")


def test_dst_overlap_requires_fold():
    local = datetime(2024, 11, 3, 1, 30)
    with pytest.raises(BirthTimeError, match="occurs twice"):
        resolve_local_birth_time(local, "America/New_York")
    earlier = resolve_local_birth_time(local, "America/New_York", fold=0)
    later = resolve_local_birth_time(local, "America/New_York", fold=1)
    assert (later - earlier).total_seconds() == 3600
