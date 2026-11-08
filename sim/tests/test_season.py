"""Tests for year-to-year season variation."""

from sim.config import SeasonConfig
from sim.domain.calendar import Calendar
from sim.implementations.season import SeasonStrategy


def _season(**overrides):
    values = dict(
        name="Summer",
        base_temperature=25.0,
        temperature_swing=6.0,
        humidity=0.40,
        pressure_hpa=1015.0,
        sun_intensity=1.15,
        daylight_fraction=0.60,
        weather_weights={"clear": 50, "cloudy": 25, "rain": 17, "storm": 8},
    )
    values.update(overrides)
    return SeasonConfig(**values)


def _calendar():
    return Calendar(ticks_per_day=10, ticks_per_season=100, season_names=["Summer"])


def test_year_one_uses_configured_baseline():
    season = _season()
    strategy = SeasonStrategy([season], ticks_per_season=100, seed=42)
    calendar = _calendar()

    palette = strategy.palette(calendar)

    assert palette.base_temperature == season.base_temperature
    assert palette.sun_intensity == season.sun_intensity
    assert strategy.weather_weights("Summer", calendar.year) == season.weather_weights


def test_later_years_vary_within_configured_ranges():
    season = _season(
        temperature_variation=3.0,
        humidity_variation=0.10,
        sun_intensity_variation=0.10,
        weather_weight_variation=0.25,
    )
    strategy = SeasonStrategy([season], ticks_per_season=100, seed=42)
    calendar = _calendar()
    calendar.tick = 100  # year 2

    palette = strategy.palette(calendar)
    weights = strategy.weather_weights("Summer", calendar.year)

    assert palette.base_temperature != season.base_temperature
    assert abs(palette.base_temperature - season.base_temperature) <= 3.0
    assert abs(palette.humidity - season.humidity) <= 0.10
    assert abs(palette.sun_intensity - season.sun_intensity) <= 0.10
    assert weights != season.weather_weights
    for kind, base_weight in season.weather_weights.items():
        assert abs(weights[kind] - base_weight) <= base_weight * 0.25


def test_same_seed_reproduces_season_sequence_and_different_seed_changes_it():
    season = _season()
    first = SeasonStrategy([season], ticks_per_season=100, seed=42)
    second = SeasonStrategy([season], ticks_per_season=100, seed=42)
    different = SeasonStrategy([season], ticks_per_season=100, seed=99)
    calendar = _calendar()
    calendar.tick = 100

    assert first.palette(calendar) == second.palette(calendar)
    assert first.weather_weights("Summer", 2) == second.weather_weights("Summer", 2)
    assert first.palette(calendar) != different.palette(calendar)


def test_zero_variation_keeps_every_year_identical():
    season = _season(
        temperature_variation=0.0,
        temperature_swing_variation=0.0,
        humidity_variation=0.0,
        pressure_variation=0.0,
        sun_intensity_variation=0.0,
        daylight_variation=0.0,
        weather_weight_variation=0.0,
    )
    strategy = SeasonStrategy([season], ticks_per_season=100, seed=42)
    calendar = _calendar()
    first = strategy.palette(calendar)
    calendar.tick = 100

    assert strategy.palette(calendar) == first


def test_snapshot_restores_variation_seed():
    season = _season()
    original = SeasonStrategy([season], ticks_per_season=100, seed=42)
    restored = SeasonStrategy([season], ticks_per_season=100, seed=99)
    restored.restore_state(original.snapshot_state())
    calendar = _calendar()
    calendar.tick = 100

    assert original.palette(calendar) == restored.palette(calendar)
