"""Behavior tests for domain models and strategies.

These tests exercise real behavior through public APIs — not unit tests for
coverage's sake. They simulate actual gameplay scenarios: creating worlds,
building environments, computing climate readings, placing beans, changing
seasons, and running day/night cycles. High coverage is a side effect of
testing real behavior, not the goal.
"""

from __future__ import annotations

import math
import pytest

from sim.config import (
    BarrierConfig,
    BeanPlacementConfig,
    EnvironmentConfig,
    GradientOrientation,
    PoissonDiscConfig,
    SeasonConfig,
    SimulationConfig,
    WorldConfig,
)
from sim.components import GameSession, GameState
from sim.container import Container
from sim.domain.calendar import Calendar
from sim.domain.climate import ClimateContext, SolarProfile
from sim.domain.gradient import Gradient
from sim.domain.visuals import SeasonPalette
from sim.domain.world import World
from sim.implementations.daynight import DayNightStrategy
from sim.implementations.season import SeasonStrategy
from sim.implementations.weather import WeatherStrategy
from sim.interfaces.world import IWorld


def _make_config(**overrides):
    """Create a SimulationConfig with at least one season."""
    cfg = SimulationConfig(
        world=WorldConfig(width=1200.0, height=800.0, cell_size=10.0),
        seasons=[
            SeasonConfig(
                name="Spring", ground_color=(96, 170, 88),
                base_temperature=14.0, temperature_swing=7.0,
                humidity=0.55, pressure_hpa=1012.0,
                sun_intensity=0.95, daylight_fraction=0.50,
                ground_meaning="growing season",
                weather_weights={"clear": 30, "cloudy": 30, "rain": 30, "storm": 10, "snow": 0},
            ),
        ],
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


# ---------------------------------------------------------------------------
# World tests
# ---------------------------------------------------------------------------


def test_world_creation_defaults():
    """A world with default cell_size derives cols/rows from width/height."""
    w = World(width=1200.0, height=800.0)
    assert w.width == 1200.0
    assert w.height == 800.0
    assert w.cell_size == 50.0
    assert w.cols == 24
    assert w.rows == 16


def test_world_cell_index_and_center():
    """World maps world positions to clamped cell indices and back to centers."""
    w = World(width=100.0, height=100.0, cell_size=10.0)
    assert w.cell_center(0, 0) == (5.0, 5.0)
    assert w.cell_center(9, 9) == (95.0, 95.0)
    assert w.cell_index(5.0, 5.0) == (0, 0)
    assert w.cell_index(95.0, 95.0) == (9, 9)
    assert w.cell_index(-5.0, -5.0) == (0, 0)
    assert w.cell_index(999.0, 999.0) == (9, 9)


def test_world_cell_bounds():
    """cell_bounds returns (left, bottom, width, height) in world units."""
    w = World(width=100.0, height=100.0, cell_size=10.0)
    left, bottom, w_, h = w.cell_bounds(0, 0)
    assert left == 0.0
    assert bottom == 0.0
    assert w_ == 10.0
    assert h == 10.0
    left, bottom, w_, h = w.cell_bounds(9, 9)
    assert left == 90.0
    assert bottom == 90.0


def test_world_barrier_validation():
    """add_barrier validates bounds and rejects out-of-world barriers."""
    w = World(width=100.0, height=100.0, cell_size=10.0)
    from sim.components import Barrier

    b = Barrier(id=1, kind="rect", x=10.0, y=10.0, width=20.0, height=20.0)
    w.add_barrier(b)
    assert len(w.barriers) == 1

    b2 = Barrier(id=2, kind="rect", x=95.0, y=10.0, width=20.0, height=20.0)
    try:
        w.add_barrier(b2)
        assert False, "Should have raised ValueError for out-of-bounds barrier"
    except ValueError:
        pass

    b3 = Barrier(id=3, kind="rect", x=10.0, y=10.0, width=0.0, height=20.0)
    try:
        w.add_barrier(b3)
        assert False, "Should have raised ValueError for zero width"
    except ValueError:
        pass


def test_world_wrap_around():
    """wrap_around=True maps coordinates outside bounds back inside."""
    w = World(width=100.0, height=100.0, cell_size=10.0, wrap_around=True)
    assert w.wrap_around is True
    assert w.clamp_or_wrap(105.0, -5.0) == (5.0, 95.0)
    assert w.clamp_or_wrap(-5.0, 105.0) == (95.0, 5.0)

    w2 = World(width=100.0, height=100.0, cell_size=10.0, wrap_around=False)
    assert w2.clamp_or_wrap(105.0, -5.0) == (100.0, 0.0)


# ---------------------------------------------------------------------------
# Gradient tests
# ---------------------------------------------------------------------------


def test_gradient_north_south():
    """north_south gradient goes from south edge (0) to north edge (1)."""
    g = Gradient(orientation=GradientOrientation.NORTH_SOUTH, start=0.0, end=10.0)
    assert g.factor(0.0, 0.0, 100.0, 100.0) == 0.0
    assert g.factor(0.0, 100.0, 100.0, 100.0) == 1.0
    assert g.factor(0.0, 50.0, 100.0, 100.0) == 0.5


def test_gradient_west_east():
    """west_east gradient goes from west edge (0) to east edge (1)."""
    g = Gradient(orientation=GradientOrientation.WEST_EAST, start=0.0, end=10.0)
    assert g.factor(0.0, 0.0, 100.0, 100.0) == 0.0
    assert g.factor(100.0, 0.0, 100.0, 100.0) == 1.0


def test_gradient_centre_out():
    """centre_out gradient goes from centre (0) to edges (1)."""
    g = Gradient(orientation=GradientOrientation.CENTRE_OUT, start=0.0, end=1.0)
    assert g.factor(50.0, 50.0, 100.0, 100.0) == 0.0
    assert g.factor(0.0, 0.0, 100.0, 100.0) == 1.0


def test_gradient_value_interpolates():
    """Gradient.value() interpolates start -> end based on factor."""
    g = Gradient(orientation=GradientOrientation.NORTH_SOUTH, start=10.0, end=20.0)
    assert g.value(0.0, 0.0, 100.0, 100.0) == 10.0
    assert g.value(0.0, 100.0, 100.0, 100.0) == 20.0
    assert g.value(0.0, 50.0, 100.0, 100.0) == 15.0


def test_gradient_signed():
    """Gradient.signed() returns symmetric values around zero."""
    g = Gradient(orientation=GradientOrientation.NORTH_SOUTH, start=-5.0, end=5.0)
    assert g.signed(0.0, 0.0, 100.0, 100.0) == -5.0
    assert g.signed(0.0, 100.0, 100.0, 100.0) == 5.0
    assert g.signed(0.0, 50.0, 100.0, 100.0) == 0.0


def test_gradient_invalid_orientation_fallback():
    """Unknown orientation falls back to north_south."""
    g = Gradient(orientation="bogus", start=0.0, end=1.0)
    assert g.orientation == GradientOrientation.NORTH_SOUTH
    assert g.factor(0.0, 0.0, 100.0, 100.0) == 0.0


# ---------------------------------------------------------------------------
# ClimateContext tests
# ---------------------------------------------------------------------------


def test_climate_context_warm_season_adjusted_weights():
    """In warm weather, rain weight increases, snow weight drops to zero."""
    solar = SolarProfile(sun_intensity=1.0, daylight_fraction=0.5)
    ctx = ClimateContext(
        tick=0,
        season="summer",
        season_progress=0.5,
        solar=solar,
        base_temperature=25.0,
        temperature_swing=7.0,
        humidity=0.5,
        pressure_hpa=1013.0,
        weather_weights={"clear": 40.0, "cloudy": 30.0, "rain": 20.0, "storm": 10.0, "snow": 0.0},
    )
    weights = ctx.adjusted_weather_weights()
    assert weights["rain"] > 0.0
    assert weights.get("snow", 0.0) == 0.0
    assert weights["clear"] > 0.0


def test_climate_context_freezing_season_rain_becomes_snow():
    """Below freezing (temp <= 1.0), rain weight is suppressed to 0 because
    the rain ramp starts at temperature=1.0."""
    solar = SolarProfile(sun_intensity=0.5, daylight_fraction=0.3)
    ctx = ClimateContext(
        tick=0,
        season="winter",
        season_progress=0.5,
        solar=solar,
        base_temperature=0.0,
        temperature_swing=5.0,
        humidity=0.8,
        pressure_hpa=1013.0,
        weather_weights={"clear": 20.0, "rain": 30.0},
    )
    weights = ctx.adjusted_weather_weights()
    assert weights.get("rain", 0.0) == 0.0
    assert weights.get("snow", 0.0) == 0.0


def test_climate_context_freezing_property():
    """is_freezing() returns True when temperature <= 1.0."""
    solar = SolarProfile(sun_intensity=1.0, daylight_fraction=0.5)
    ctx = ClimateContext(
        tick=0, season="winter", season_progress=0.5, solar=solar,
        base_temperature=0.0, temperature_swing=5.0, humidity=0.5,
        pressure_hpa=1013.0,
    )
    assert ctx.is_freezing() is True

    ctx2 = ClimateContext(
        tick=0, season="winter", season_progress=0.5, solar=solar,
        base_temperature=15.0, temperature_swing=5.0, humidity=0.5,
        pressure_hpa=1013.0,
    )
    assert ctx2.is_freezing() is False


def test_climate_context_humidity_band():
    """humidity_band categorizes humidity levels."""
    solar = SolarProfile(sun_intensity=1.0, daylight_fraction=0.5)
    ctx_dry = ClimateContext(
        tick=0, season="spring", season_progress=0.5, solar=solar,
        base_temperature=14.0, temperature_swing=7.0,
        humidity=0.2, pressure_hpa=1013.0,
    )
    assert ctx_dry.humidity_band() == "dry"

    ctx_temperate = ClimateContext(
        tick=0, season="spring", season_progress=0.5, solar=solar,
        base_temperature=14.0, temperature_swing=7.0,
        humidity=0.5, pressure_hpa=1013.0,
    )
    assert ctx_temperate.humidity_band() == "temperate"

    ctx_humid = ClimateContext(
        tick=0, season="spring", season_progress=0.5, solar=solar,
        base_temperature=14.0, temperature_swing=7.0,
        humidity=0.8, pressure_hpa=1013.0,
    )
    assert ctx_humid.humidity_band() == "humid"


def test_climate_context_sun_angle_hint():
    """sun_angle_hint returns sine of daylight fraction."""
    solar = SolarProfile(sun_intensity=1.0, daylight_fraction=0.5)
    ctx = ClimateContext(
        tick=0, season="spring", season_progress=0.5, solar=solar,
        base_temperature=14.0, temperature_swing=7.0,
        humidity=0.5, pressure_hpa=1013.0,
    )
    assert abs(ctx.sun_angle_hint() - math.sin(math.pi * 0.5)) < 1e-6


def test_climate_context_from_palette():
    """from_palette builds a ClimateContext from a SeasonPalette."""
    palette = SeasonPalette(
        name="Spring", ground=(96, 170, 88), details=((140, 170, 140),),
        base_temperature=14.0, temperature_swing=7.0,
        humidity=0.55, pressure_hpa=1012.0,
        sun_intensity=0.95, daylight_fraction=0.50,
        ground_meaning="growing season",
    )
    w = World(width=1200.0, height=800.0, cell_size=10.0)
    ctx = ClimateContext.from_palette(
        tick=100, season="spring", season_progress=0.3,
        palette=palette, solar=SolarProfile(sun_intensity=0.95, daylight_fraction=0.5),
        weather_weights={"clear": 40.0, "rain": 20.0}, world=w,
    )
    assert ctx.season == "spring"
    assert ctx.base_temperature == 14.0
    assert ctx.cols == 120
    assert ctx.rows == 80


# ---------------------------------------------------------------------------
# DayNightStrategy tests
# ---------------------------------------------------------------------------


def test_daynight_light_at_midnight_is_zero():
    """At midnight (day_fraction=0), sun altitude is 0 so light is 0."""
    cfg = _make_config()
    container = Container(cfg)
    strategy = container.environment._daynight_strategy
    cal = container.environment.calendar
    cal._tick = 0
    light = strategy.light_at(cal, 600.0, 400.0, solar=container.environment.solar)
    assert light == 0.0


def test_daynight_phase_night():
    """At midnight, phase is 'night'."""
    cfg = _make_config()
    container = Container(cfg)
    cal = container.environment.calendar
    cal._tick = 0
    phase = container.environment.phase
    assert phase == "night"


# ---------------------------------------------------------------------------
# SeasonStrategy tests
# ---------------------------------------------------------------------------


def test_season_strategy_palette():
    """SeasonStrategy.palette returns a SeasonPalette with all fields."""
    seasons = [
        SeasonConfig(
            name="Spring", ground_color=(96, 170, 88),
            base_temperature=14.0, temperature_swing=7.0,
            humidity=0.55, pressure_hpa=1012.0,
            sun_intensity=0.95, daylight_fraction=0.50,
            ground_meaning="growing season",
        ),
    ]
    strategy = SeasonStrategy(seasons=seasons, ticks_per_season=4800)
    cal = Calendar(ticks_per_day=1200, ticks_per_season=4800, season_names=["Spring"])
    palette = strategy.palette(cal)
    assert palette.name == "Spring"
    assert palette.ground_meaning == "growing season"
    assert palette.sun_intensity == 0.95


def test_season_strategy_solar_profile():
    """solar_profile returns a SolarProfile with season's sun values."""
    seasons = [
        SeasonConfig(
            name="Summer", ground_color=(68, 146, 72),
            base_temperature=25.0, temperature_swing=6.0,
            humidity=0.40, pressure_hpa=1015.0,
            sun_intensity=1.15, daylight_fraction=0.60,
            ground_meaning="peak growing season",
        ),
    ]
    strategy = SeasonStrategy(seasons=seasons, ticks_per_season=4800)
    cal = Calendar(ticks_per_day=1200, ticks_per_season=4800, season_names=["Summer"])
    profile = strategy.solar_profile(cal)
    assert profile.sun_intensity == 1.15
    assert profile.daylight_fraction == 0.60


# ---------------------------------------------------------------------------
# WeatherStrategy tests
# ---------------------------------------------------------------------------


def test_weather_strategy_update_builds_field():
    """WeatherStrategy.update() builds a field based on climate context."""
    cfg = _make_config()
    container = Container(cfg)
    env = container.environment
    strategy = env.weather_strategy
    assert strategy is not None

    ctx = env.climate_context()
    strategy.update(0, ctx)
    assert strategy.weather in ("clear", "cloudy", "rain", "storm", "snow")


def test_weather_strategy_weather_at_cell():
    """weather_at_cell returns a condition for any cell."""
    cfg = _make_config()
    container = Container(cfg)
    strategy = container.environment.weather_strategy
    ctx = container.environment.climate_context()
    strategy.update(0, ctx)

    for col in range(0, 120, 10):
        for row in range(0, 80, 10):
            condition = strategy.weather_at_cell(col, row)
            assert condition in ("clear", "cloudy", "rain", "storm", "snow")


# ---------------------------------------------------------------------------
# GameSession / KeyboardInput tests
# ---------------------------------------------------------------------------


def test_game_session_initial_state():
    """GameSession starts in START state with paused clock."""
    from sim.components import GameSession
    session = GameSession()
    assert session.state.name == "START"
    assert session.clock.paused is True


def test_keyboard_input_start_to_playing():
    """KeyboardInput SPACE transitions START -> PLAYING."""
    from sim.components import GameSession
    from sim.input.keyboard import KeyboardInput
    session = GameSession()
    kb = KeyboardInput(session)
    kb.handle_keypress(32)
    assert session.state.name == "PLAYING"
    assert session.clock.paused is False


def test_keyboard_input_playing_to_paused():
    """KeyboardInput P transitions PLAYING -> PAUSED."""
    from sim.components import GameSession
    from sim.input.keyboard import KeyboardInput
    session = GameSession()
    kb = KeyboardInput(session)
    kb.handle_keypress(32)
    kb.handle_keypress(112)
    assert session.state.name == "PAUSED"
    assert session.clock.paused is True


def test_keyboard_input_config_state():
    """KeyboardInput C transitions PLAYING -> CONFIG, C again returns to PLAYING."""
    from sim.components import GameSession
    from sim.input.keyboard import KeyboardInput
    session = GameSession()
    kb = KeyboardInput(session)
    kb.handle_keypress(32)
    kb.handle_keypress(99)
    assert session.state.name == "CONFIG"
    kb.handle_keypress(99)
    assert session.state.name == "PLAYING"


def test_keyboard_input_set_time_scale():
    """set_time_scale clamps to [0.1, 4.0]."""
    from sim.components import GameSession
    from sim.input.keyboard import KeyboardInput
    session = GameSession()
    kb = KeyboardInput(session)
    kb.handle_keypress(32)
    kb.set_time_scale(0.5)
    assert session.clock.time_scale == 0.5
    kb.set_time_scale(99.0)
    assert session.clock.time_scale == 4.0
    kb.set_time_scale(0.01)
    assert session.clock.time_scale == 0.1


# ---------------------------------------------------------------------------
# GameSession beans tests
# ---------------------------------------------------------------------------


def test_session_contains_beans_after_container_build():
    """Container generates beans and stores them in session.beans."""
    cfg = _make_config()
    container = Container(cfg)
    assert len(container.session.beans) > 0
    for bean in container.session.beans:
        assert bean.gender in ("male", "female")
        assert bean.color in ((0, 0, 255), (255, 0, 0))
        assert 0.0 <= bean.x <= 1200.0
        assert 0.0 <= bean.y <= 800.0


def test_beans_have_gender_balance():
    """Bean gender ratio is approximately 50/50 by default."""
    cfg = _make_config()
    container = Container(cfg)
    beans = container.session.beans
    males = sum(1 for b in beans if b.gender == "male")
    females = sum(1 for b in beans if b.gender == "female")
    total = len(beans)
    assert males + females == total
    assert abs(males / total - 0.5) < 0.15


# ---------------------------------------------------------------------------
# GradientOrientation enum tests
# ---------------------------------------------------------------------------


def test_gradient_orientation_enum_values():
    """GradientOrientation enum has all expected values."""
    assert GradientOrientation.NORTH_SOUTH.value == "north_south"
    assert GradientOrientation.SOUTH_NORTH.value == "south_north"
    assert GradientOrientation.WEST_EAST.value == "west_east"
    assert GradientOrientation.EAST_WEST.value == "east_west"
    assert GradientOrientation.CENTRE_OUT.value == "centre_out"
    assert GradientOrientation.OUT_CENTRE.value == "out_centre"
    assert GradientOrientation.DIAGONAL_UP.value == "diagonal_up"
    assert GradientOrientation.DIAGONAL_DOWN.value == "diagonal_down"


# ---------------------------------------------------------------------------
# Calendar tests
# ---------------------------------------------------------------------------


def test_calendar_validation():
    """Calendar rejects invalid configuration."""
    from sim.domain.calendar import Calendar
    with pytest.raises(ValueError):
        Calendar(ticks_per_day=0, ticks_per_season=4800, season_names=["Spring"])
    with pytest.raises(ValueError):
        Calendar(ticks_per_day=1200, ticks_per_season=0, season_names=["Spring"])
    with pytest.raises(ValueError):
        Calendar(ticks_per_day=1200, ticks_per_season=4800, season_names=[])


def test_calendar_tick_setter():
    """Calendar tick setter clamps to 0."""
    from sim.domain.calendar import Calendar
    cal = Calendar(ticks_per_day=1200, ticks_per_season=4800, season_names=["Spring"])
    cal.tick = 100
    assert cal.tick == 100
    cal.tick = -5
    assert cal.tick == 0


def test_calendar_properties():
    """Calendar derives day, season, phase, year from tick."""
    from sim.domain.calendar import Calendar
    cal = Calendar(ticks_per_day=1200, ticks_per_season=4800, season_names=["Spring", "Summer"])
    cal.advance(0)
    assert cal.day == 1
    assert cal.season == "Spring"
    assert cal.season_index == 0
    assert cal.year == 1

    cal.advance(1200)
    assert cal.day == 2
    assert cal.day_fraction == 0.0

    cal.advance(600)
    assert cal.clock == "12:00"

    cal.advance(4800)
    assert cal.season == "Summer"
    assert cal.season_index == 1
    assert cal.year == 1

    cal.advance(4800)
    assert cal.year == 2


def test_calendar_season_progress():
    """season_progress and day_of_season derived from tick."""
    from sim.domain.calendar import Calendar
    cal = Calendar(ticks_per_day=1200, ticks_per_season=4800, season_names=["Spring"])
    cal.advance(600)
    assert cal.day_fraction == 0.5
    assert cal.day_of_season == 1
    cal.advance(1200)
    assert cal.day_of_season == 2
    assert cal.days_per_season == 4


# ---------------------------------------------------------------------------
# Environment static mode tests
# ---------------------------------------------------------------------------


def test_environment_static_mode():
    """Environment with no strategies uses static fallbacks."""
    from sim.domain.environment import Environment
    from sim.domain.calendar import Calendar
    from sim.config import LoggingConfig
    cal = Calendar(ticks_per_day=1200, ticks_per_season=4800, season_names=["Spring"])
    env = Environment(calendar=cal)
    assert env.season == "Spring"
    assert env.weather == "clear"
    assert env.phase == "day"
    assert env.palette.name == "Static"


def test_environment_light_at_no_strategy():
    """light_at returns a value between 0 and 1 with no daynight strategy."""
    from sim.domain.environment import Environment
    from sim.domain.calendar import Calendar
    cal = Calendar(ticks_per_day=1200, ticks_per_season=4800, season_names=["Spring"])
    env = Environment(calendar=cal)
    light = env.light_at(100.0, 200.0)
    assert 0.0 <= light <= 1.0


# ---------------------------------------------------------------------------
# KeyboardInput key_ignored tests
# ---------------------------------------------------------------------------


def test_keyboard_input_key_ignored():
    """KeyboardInput ignores unknown keys."""
    from sim.components import GameSession
    from sim.input.keyboard import KeyboardInput
    session = GameSession()
    kb = KeyboardInput(session)
    session.state = GameState.PLAYING
    kb.handle_keypress(999)
    assert session.state.name == "PLAYING"


def test_keyboard_input_quit_from_playing():
    """KeyboardInput Q from PLAYING transitions to END."""
    from sim.components import GameSession
    from sim.input.keyboard import KeyboardInput
    session = GameSession()
    kb = KeyboardInput(session)
    kb.handle_keypress(32)  # Start -> PLAYING
    kb.handle_keypress(113)  # Q -> END
    assert session.state.name == "END"
    assert session.exit_requested is True


# ---------------------------------------------------------------------------
# Environment strategy tests
# ---------------------------------------------------------------------------


def test_environment_with_daynight_strategy():
    """Environment uses daynight strategy when available."""
    from sim.domain.environment import Environment
    from sim.domain.calendar import Calendar
    cfg = _make_config()
    container = Container(cfg)
    env = container.environment
    assert env.daynight_strategy is not None
    light = env.light_at(100.0, 200.0)
    assert 0.0 <= light <= 1.0


def test_environment_weather_at():
    """Environment.weather_at delegates to weather strategy."""
    cfg = _make_config()
    container = Container(cfg)
    env = container.environment
    condition = env.weather_at(100.0, 200.0)
    assert condition in ("clear", "cloudy", "rain", "storm", "snow")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
