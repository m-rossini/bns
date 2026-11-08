"""Behavior tests for the day/night and energy strategies.

Day/night shapes the season's sun into light, phases and sky; energy turns
config rates into per-bean gains. These tests walk full day cycles and
state transitions rather than asserting implementation details.
"""

from __future__ import annotations

import pytest

from sim.config import DayNightConfig, EnergyConfig
from sim.domain.beans import Bean
from sim.domain.calendar import Calendar
from sim.domain.genotype import DEFAULT_GENOTYPE, create_default_phenotype
from sim.domain.visuals import SolarProfile
from sim.implementations.daynight import DayNightStrategy
from sim.implementations.energy.fixed_energy import (
    FixedEnergyStrategy,
    PerDayEnergyStrategy,
)


def _calendar_at(tick: int, ticks_per_day: int = 1200) -> Calendar:
    calendar = Calendar(
        ticks_per_day=ticks_per_day,
        ticks_per_season=ticks_per_day * 4,
        season_names=["Spring", "Summer", "Autumn", "Winter"],
    )
    calendar.tick = tick
    return calendar


def _summer_sun() -> SolarProfile:
    return SolarProfile(sun_intensity=1.15, daylight_fraction=0.60)


def _bean(bean_id: int, energy: float = 500.0, dormant: bool = False) -> Bean:
    phenotype = create_default_phenotype(DEFAULT_GENOTYPE)
    phenotype.current_energy = energy
    phenotype.is_dormant = dormant
    return Bean(
        id=bean_id,
        x=10.0,
        y=10.0,
        gender="female",
        color=DEFAULT_GENOTYPE.base_color,
        genotype=DEFAULT_GENOTYPE,
        phenotype=phenotype,
    )


# ---------------------------------------------------------------------------
# Day/night
# ---------------------------------------------------------------------------


def test_daynight_rejects_non_positive_day_length():
    """A day must contain at least one tick."""
    with pytest.raises(ValueError):
        DayNightStrategy(config=DayNightConfig(), ticks_per_day=0)


def test_noon_is_bright_and_midnight_is_dark():
    """Light peaks midday and vanishes at night for the same cell."""
    strategy = DayNightStrategy(config=DayNightConfig(), ticks_per_day=1200)
    solar = _summer_sun()

    assert strategy.light_at(_calendar_at(600), 100.0, 100.0, solar) > 0.5
    assert strategy.light_at(_calendar_at(0), 100.0, 100.0, solar) == 0.0


def test_stronger_sun_means_brighter_noon_and_longer_days():
    """The season's solar profile scales both peak light and day length."""
    strategy = DayNightStrategy(config=DayNightConfig(), ticks_per_day=1200)
    bright = SolarProfile(sun_intensity=1.5, daylight_fraction=0.80)
    dim = SolarProfile(sun_intensity=0.4, daylight_fraction=0.20)

    assert strategy.light_at(_calendar_at(600), 0.0, 0.0, bright) > \
        strategy.light_at(_calendar_at(600), 0.0, 0.0, dim)
    # With a short day, early morning is still night; with a long day it is not.
    assert strategy.phase(_calendar_at(180), dim) == "night"
    assert strategy.phase(_calendar_at(180), bright) != "night"


def test_full_day_cycles_through_all_phases_in_order():
    """A day runs night -> dawn -> day -> dusk -> night."""
    strategy = DayNightStrategy(config=DayNightConfig(), ticks_per_day=1200)
    solar = _summer_sun()

    phases = [strategy.phase(_calendar_at(tick), solar) for tick in range(1200)]

    assert phases[0] == "night"
    assert "dawn" in phases and "day" in phases and "dusk" in phases
    first_dawn = phases.index("dawn")
    first_day = phases.index("day")
    first_dusk = phases.index("dusk")
    assert first_dawn < first_day < first_dusk
    assert phases[-1] == "night"


def test_sun_and_moon_trade_places_and_moon_has_phases():
    """The sun shows by day, the moon by night, with 0..1 illumination."""
    strategy = DayNightStrategy(config=DayNightConfig(), ticks_per_day=1200)
    solar = _summer_sun()

    noon = strategy.celestial(_calendar_at(600), solar)
    midnight = strategy.celestial(_calendar_at(0), solar)

    assert noon.sun_visible and not noon.moon_visible
    assert midnight.moon_visible and not midnight.sun_visible
    assert 0.0 <= midnight.moon_illumination <= 1.0


def test_sky_palette_comes_from_config():
    """Sky colours are data, not hardcoded in the strategy."""
    config = DayNightConfig(night_sky=(1, 2, 3), day_sky=(4, 5, 6))
    strategy = DayNightStrategy(config=config, ticks_per_day=1200)

    palette = strategy.sky_palette()

    assert palette.night == (1, 2, 3)
    assert palette.day == (4, 5, 6)
    assert strategy.ticks_per_day == 1200


# ---------------------------------------------------------------------------
# Energy
# ---------------------------------------------------------------------------


def test_fixed_gain_pays_awake_beans_and_skips_dormant_ones():
    """Only living, phenotyped beans earn the per-tick rate."""
    strategy = FixedEnergyStrategy(
        config=EnergyConfig(strategy_name="fixed", energy_per_tick=2.0)
    )
    awake = _bean(1)
    dormant = _bean(2, energy=0.0, dormant=True)
    no_body = _bean(3)
    no_body.phenotype = None

    gains = strategy.calculate_energy_gain(
        [awake, dormant, no_body], environment=None, world=None, dt=1.5
    )

    assert gains == {1: 2.0 * 1.5}


def test_fixed_gain_disabled_by_zero_rate():
    """A zero rate pays nobody, however awake."""
    strategy = FixedEnergyStrategy(
        config=EnergyConfig(strategy_name="fixed", energy_per_tick=0.0)
    )

    assert strategy.calculate_energy_gain(
        [_bean(1)], environment=None, world=None, dt=1.0
    ) == {}


def test_per_day_pays_once_per_day_boundary():
    """The lump sum lands on the first tick of each day, then stays quiet."""
    strategy = PerDayEnergyStrategy(
        config=EnergyConfig(strategy_name="per_day", energy_per_day=50.0)
    )

    class _Env:
        def __init__(self, calendar):
            self.calendar = calendar

    calendar = _calendar_at(0)
    env = _Env(calendar)

    first = strategy.calculate_energy_gain(
        [_bean(1), _bean(2)], environment=env, world=None, dt=1.0
    )
    repeat = strategy.calculate_energy_gain(
        [_bean(1)], environment=env, world=None, dt=1.0
    )
    calendar.tick = 1200  # next day
    second = strategy.calculate_energy_gain(
        [_bean(1)], environment=env, world=None, dt=1.0
    )

    assert first == {1: 50.0, 2: 50.0}
    assert repeat == {}
    assert second == {1: 50.0}


def test_per_day_needs_a_calendar():
    """Without an environment or calendar there is no day to pay on."""
    strategy = PerDayEnergyStrategy(
        config=EnergyConfig(strategy_name="per_day", energy_per_day=50.0)
    )

    assert strategy.calculate_energy_gain(
        [_bean(1)], environment=None, world=None, dt=1.0
    ) == {}
