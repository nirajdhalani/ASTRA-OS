import pytest

from app.astro.ephemeris import (
    BODY_KEY_CANDIDATES,
    EphemerisUnavailable,
    SkyfieldProvider,
    resolve_body_keys,
)


class FakeKernel:
    """Minimal stand-in for the target lookup supported by a Skyfield SPK."""
    def __init__(self, targets):
        self.targets = {name.lower() for name in targets}

    def __getitem__(self, name):
        normalized = name.lower()
        if normalized not in self.targets:
            raise KeyError(normalized)
        return object()


def test_resolves_de440s_planetary_targets_including_mars_barycenter():
    # These names reflect the target set reported by the DE440s kernel.
    kernel = FakeKernel({
        "sun",
        "moon",
        "mercury",
        "venus",
        "mars barycenter",
        "jupiter barycenter",
        "saturn barycenter",
        "uranus barycenter",
        "neptune barycenter",
        "pluto barycenter",
    })

    resolved = resolve_body_keys(kernel)

    assert resolved["Mars"] == "mars barycenter"
    assert resolved["Jupiter"] == "jupiter barycenter"
    assert resolved["Pluto"] == "pluto barycenter"
    assert set(resolved) == set(BODY_KEY_CANDIDATES)


def test_prefers_planet_center_when_kernel_exposes_it():
    kernel = FakeKernel({
        "sun", "moon", "mercury", "venus", "mars", "mars barycenter",
        "jupiter barycenter", "saturn barycenter", "uranus barycenter",
        "neptune barycenter", "pluto barycenter",
    })

    assert resolve_body_keys(kernel)["Mars"] == "mars"


def test_missing_kernel_target_raises_actionable_error():
    kernel = FakeKernel({"sun", "moon"})

    with pytest.raises(EphemerisUnavailable, match="does not contain a target for Mercury"):
        resolve_body_keys(kernel)


def test_positions_iterates_every_configured_body():
    provider = SkyfieldProvider.__new__(SkyfieldProvider)
    requested = []

    def fake_longitude(body_name, utc_dt):
        requested.append(body_name)
        return 15.0

    provider.longitude = fake_longitude
    from datetime import datetime, timezone

    result = provider.positions(datetime(2026, 1, 1, tzinfo=timezone.utc))

    assert set(requested) == set(BODY_KEY_CANDIDATES)
    assert set(result) == set(BODY_KEY_CANDIDATES)
    assert all(value["tropical_longitude"] == 15.0 for value in result.values())
