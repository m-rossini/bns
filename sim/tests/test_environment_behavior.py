"""Behavior tests for the composed Environment.

The environment turns calendar time + strategies into the physical readings
beans live in. These tests check observable behavior: static fallbacks with no
strategies, day/season/weather transitions as ticks advance, readings that
respond to light and position, and reset/snapshot round-trips.
"""

from __future__ import annotations

import logging

from sim.config import (
    BeanPlacementConfig,
    EnvironmentConfig,
    PoissonDiscConfig,
    SeasonConfig,
    SimulationConfig,
    WeatherConfig,
    WorldConfig,
)
from sim.container import Container
from sim.domain.calendar import Calendar
from sim.domain.climate import DEFAULT_WEATHER_WEIGHTS
from sim.domain.environment import Environment


def _season(**overrides):
    values = dict(
        name="Spring",
        ground_color=(96, 170, 88),
        base_temperature=14.0,
        temperature_swing=7.0,
        humidity=0.55,
        pressure_hpa=1012.0,
        sun_intensity=0.95,
        daylight_fraction=0.50,
        ground_meaning="growing season",
        weather_weights={"clear": 50, "cloudy": 50},
    )
    values.update(overrides)
    return SeasonConfig(**values)


def _make_config(**overrides):
    cfg = SimulationConfig(
        world=WorldConfig(width=200.0, height=200.0, cell_size=10.0),
        seasons=[_season()],
        bean_placement=BeanPlacementConfig(
            strategy_name="poisson_disc",
            density_tier="average",
            variance=0.0,
            seed=42,
            gender_ratios={"male": 50.0, "female": 50.0},
            gender_colors={"male": (0, 0, 255), "female": (255, 0, 0)},
            bean_radius=5.0,
            poisson_disc=PoissonDiscConfig(),
        ),
        environment=EnvironmentConfig(
            weather_strategy="WeatherStrategy",
            season_strategy="SeasonStrategy",
            daynight_strategy="DayNightStrategy",
        ),
    )
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


def _bare_environment():
    calendar = Calendar(ticks_per_day=1200, ticks_per_season=4800,
                        season_names=["Spring"])
    return Environment(calendar=calendar)


# ---------------------------------------------------------------------------
# Static fallbacks (no strategies wired)
# ---------------------------------------------------------------------------


def test_bare_environment_reports_static_readings():
    """With no strategies, the world still answers with documented defaults."""
    env = _bare_environment()

    assert env.tick == 0
    assert env.season == "Spring"
    assert env.phase == "day"
    assert env.weather == "clear"
    assert env.weather_weights() == {}
    assert 0.0 <= env.light_level <= 1.0

    palette = env.palette
    solar = env.solar
    celestial = env.celestial
    assert palette.name == "Static"
    assert solar.sun_intensity == 1.0
    assert celestial is not None


def test_bare_environment_climate_uses_default_weights():
    """Climate snapshots without a season fall back to the default weights."""
    env = _bare_environment()

    ctx = env.climate_context()
    assert dict(ctx.weather_weights) == dict(DEFAULT_WEATHER_WEIGHTS)


def test_bare_environment_counts_single_cell():
    """Without a world there is exactly one implicit cell to census."""
    env = _bare_environment()

    assert env._weather_cell_counts() == {"clear": 1}


def test_environment_exposes_its_wiring():
    """Identity accessors report the calendar, configs and strategies."""
    container = Container(_make_config())
    env = container.environment

    assert env.tick == env.calendar.tick
    assert env.config is container.config.environment
    assert env.weather_config is container.config.weather
    assert env.season_strategy is container.environment.season_strategy
    assert env.daynight_strategy is not None
    assert env.weather_strategy is not None


# ---------------------------------------------------------------------------
# Positional readings
# ---------------------------------------------------------------------------


def test_noon_is_warmer_than_midnight_at_the_same_place():
    """Light drives temperature: midday readings exceed midnight ones."""
    container = Container(_make_config())
    env = container.environment
    x, y = 100.0, 100.0

    env.calendar.tick = 0  # midnight: no sun
    midnight = env.temperature_at(x, y)
    env.calendar.tick = 600  # midday: sun at its peak
    noon = env.temperature_at(x, y)

    assert noon > midnight


def test_readings_vary_across_the_world_and_stay_physical():
    """Gradients and microclimate make distant cells report different values."""
    container = Container(_make_config())
    env = container.environment

    near = (20.0, 20.0)
    far = (180.0, 180.0)
    assert env.temperature_at(*near) != env.temperature_at(*far)
    for point in (near, far):
        assert 0.0 <= env.humidity_at(*point) <= 1.0
        assert 900.0 <= env.pressure_at(*point) <= 1100.0
        assert 0.0 <= env.light_at(*point) <= 1.0


def test_world_census_covers_every_cell():
    """The weather census counts each grid cell exactly once."""
    container = Container(_make_config())
    env = container.environment

    counts = env._weather_cell_counts()
    assert sum(counts.values()) == env._world.cols * env._world.rows


# ---------------------------------------------------------------------------
# Tick transitions
# ---------------------------------------------------------------------------


def test_crossing_midnight_logs_a_new_day(caplog):
    """Advancing past the day boundary emits the day event."""
    container = Container(_make_config())
    env = container.environment

    with caplog.at_level(logging.INFO, logger="bean.environment"):
        for _ in range(1200):
            env.advance_tick()

    assert env.calendar.day == 2
    assert any("environment.day_changed" in record.message
               for record in caplog.records)


def test_crossing_season_boundary_logs_a_new_season(caplog):
    """Advancing past the season boundary emits the season event."""
    cfg = _make_config()
    cfg.seasons = [cfg.seasons[0], _season(name="Summer", base_temperature=25.0)]
    container = Container(cfg)
    env = container.environment

    with caplog.at_level(logging.INFO, logger="bean.environment"):
        for _ in range(4800):
            env.advance_tick()

    assert env.calendar.season == "Summer"
    assert env.calendar.year == 1
    assert any("environment.season_changed" in record.message
               for record in caplog.records)


def test_changing_weather_logs_a_census(caplog):
    """When the aggregate condition flips, the event carries cell counts."""
    cfg = _make_config(
        weather=WeatherConfig(change_interval=1, seed=7, front_count=2,
                              background_coverage=0.6,
                              front_radius_min_cells=2,
                              front_radius_max_cells=4),
    )
    container = Container(cfg)
    env = container.environment

    with caplog.at_level(logging.INFO, logger="bean.environment"):
        for _ in range(40):
            env.advance_tick()
            if any("environment.weather_changed" in record.message
                   for record in caplog.records):
                break

    assert any("environment.weather_changed" in record.message
               for record in caplog.records)
    assert env._last_weather == env.weather


def test_debug_readings_sample_the_reference_cell(caplog):
    """With DEBUG readings on, ticks periodically log a full reading sample."""
    cfg = _make_config()
    cfg.logging.readings_interval = 1
    container = Container(cfg)
    env = container.environment

    with caplog.at_level(logging.DEBUG, logger="bean.environment"):
        for _ in range(3):
            env.advance_tick()

    assert any("environment.reading" in record.message
               for record in caplog.records)


def test_reset_returns_to_tick_zero_and_clears_caches():
    """Reset rewinds the calendar and drops derived palette/solar caches."""
    container = Container(_make_config())
    env = container.environment
    for _ in range(2500):
        env.advance_tick()
    assert env.calendar.tick == 2500

    env.reset()

    assert env.calendar.tick == 0
    assert env.palette.name == "Spring"
    assert env.solar.sun_intensity == 0.95
