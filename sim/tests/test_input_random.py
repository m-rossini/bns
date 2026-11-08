"""Behavior tests for keyboard input, the game clock and the RNG helpers.

Keyboard input drives the session state machine; the clock helpers pause,
resume and scale playback; the random module is the single entropy source.
Each test observes state changes, not internals.
"""

from __future__ import annotations

import math
import random as stdlib_random

import pytest

from sim.components import GameState
from sim.config import (
    BeanPlacementConfig,
    EnvironmentConfig,
    PoissonDiscConfig,
    SeasonConfig,
    SimulationConfig,
    WorldConfig,
)
from sim.container import Container
from sim.input.keyboard import (
    KEY_C,
    KEY_ESCAPE,
    KEY_P,
    KEY_Q,
    KEY_SPACE,
    KeyboardInput,
)
from sim.time import game_clock
from sim import random as sim_random
from sim.random import RandomConfig


def _make_config(**overrides):
    cfg = SimulationConfig(
        world=WorldConfig(width=200.0, height=200.0, cell_size=10.0),
        seasons=[
            SeasonConfig(
                name="Spring", ground_color=(96, 170, 88),
                base_temperature=14.0, temperature_swing=7.0,
                humidity=0.55, pressure_hpa=1012.0,
                sun_intensity=0.95, daylight_fraction=0.50,
                ground_meaning="growing season",
                weather_weights={"clear": 50, "cloudy": 50},
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


def _session():
    return Container(_make_config()).session


# ---------------------------------------------------------------------------
# Keyboard state machine
# ---------------------------------------------------------------------------


def test_space_starts_the_game_from_title():
    """SPACE on the title screen starts a running simulation."""
    session = _session()
    assert session.state == GameState.START

    KeyboardInput(session).handle_keypress(KEY_SPACE)

    assert session.state == GameState.PLAYING
    assert session.clock.paused is False


def test_title_screen_pause_quit_and_ignored_keys():
    """P pauses, ESC quits, anything else leaves the title alone."""
    session = _session()
    keys = KeyboardInput(session)

    keys.handle_keypress(KEY_P)
    assert session.state == GameState.PAUSED
    assert session.clock.paused is True

    session2 = _session()
    keys2 = KeyboardInput(session2)
    keys2.handle_keypress(KEY_ESCAPE)
    assert session2.state == GameState.END
    assert session2.exit_requested is True

    session3 = _session()
    KeyboardInput(session3).handle_keypress(KEY_Q)
    assert session3.state == GameState.START  # Q is ignored on START


def test_playing_pause_config_quit_and_ignored_keys():
    """PLAYING fans out to pause, config, quit; other keys are ignored."""
    session = _session()
    session.state = GameState.PLAYING
    keys = KeyboardInput(session)

    keys.handle_keypress(KEY_C)
    assert session.state == GameState.CONFIG

    keys.handle_keypress(KEY_C)
    assert session.state == GameState.PLAYING

    keys.handle_keypress(KEY_P)
    assert session.state == GameState.PAUSED

    keys.handle_keypress(KEY_P)
    assert session.state == GameState.PLAYING
    assert session.clock.paused is False

    keys.handle_keypress(KEY_Q)
    assert session.state == GameState.END
    assert session.end_reason == "user quit"

    paused_session = _session()
    paused_session.state = GameState.PAUSED
    KeyboardInput(paused_session).handle_keypress(KEY_Q)
    assert paused_session.state == GameState.END

    config_session = _session()
    config_session.state = GameState.CONFIG
    KeyboardInput(config_session).handle_keypress(KEY_ESCAPE)
    assert config_session.state == GameState.PLAYING

    keys.handle_keypress(999)  # unknown keys never change state
    assert session.state == GameState.END


def test_end_screen_restarts_or_closes():
    """SPACE restarts a finished run; ESC closes it."""
    session = _session()
    session.state = GameState.END
    session.end_reason = "extinction"
    session.corpses.append(object())
    session.deaths_old_age = 3
    session.deaths_starvation = 4
    keys = KeyboardInput(session)

    keys.handle_keypress(KEY_SPACE)

    assert session.state == GameState.START
    assert session.end_reason is None
    assert session.corpses == []
    assert session.deaths_old_age == 0
    assert session.deaths_starvation == 0

    session.state = GameState.END
    keys.handle_keypress(KEY_ESCAPE)
    assert session.exit_requested is True


def test_time_scale_is_clamped_and_leaves_tick_rate_alone():
    """Playback speed stays in range and never touches the fixed tick rate."""
    session = _session()
    keys = KeyboardInput(session)
    before = session.clock.tick

    keys.set_time_scale(99.0)
    assert session.clock.time_scale == 4.0
    keys.set_time_scale(-5.0)
    assert session.clock.time_scale == 0.1
    assert session.clock.tick == before


def test_clock_pause_resume_and_toggle():
    """Pause helpers flip the paused flag and report the new state."""
    session = _session()

    game_clock.pause(session.clock)
    assert session.clock.paused is True
    game_clock.resume(session.clock)
    assert session.clock.paused is False
    assert game_clock.toggle_pause(session.clock) is True
    assert game_clock.toggle_pause(session.clock) is False


# ---------------------------------------------------------------------------
# Random module
# ---------------------------------------------------------------------------


def test_seeded_runs_reproduce_and_unseeded_runs_vary():
    """The same seed replays the same draws; fresh entropy does not repeat."""
    sim_random.init_random(RandomConfig(seed=1234))
    first = [sim_random.get_rng().random() for _ in range(5)]

    sim_random.init_random(RandomConfig(seed=1234))
    second = [sim_random.get_rng().random() for _ in range(5)]

    sim_random.init_random(RandomConfig(seed=None))
    assert sim_random.get_rng() is not None

    assert first == second


def test_drawing_helpers_stay_in_range_and_shuffle():
    """Direction is a unit vector; draws respect bounds; shuffle keeps items."""
    rng = stdlib_random.Random(99)

    dx, dy = sim_random.random_direction(rng)
    assert math.isclose(dx * dx + dy * dy, 1.0, rel_tol=1e-9)
    assert 1.0 <= sim_random.random_float(rng, 1.0, 2.0) < 2.0
    assert 1 <= sim_random.random_int(rng, 1, 6) <= 6
    assert sim_random.random_choice(["a", "b"], rng) in ("a", "b")

    items = [1, 2, 3, 4, 5]
    sim_random.random_shuffle(items, rng)
    assert sorted(items) == [1, 2, 3, 4, 5]


def test_helpers_fall_back_to_the_shared_generator():
    """Calling helpers without an RNG uses (and initialises) the global one."""
    sim_random.init_random(RandomConfig(seed=7))

    assert 0.0 <= sim_random.random_float() < 1.0
    assert 0 <= sim_random.random_int(a=0, b=10) <= 10
    assert sim_random.random_choice([1]) == 1
    dx, dy = sim_random.random_direction()
    assert math.isclose(dx * dx + dy * dy, 1.0, rel_tol=1e-9)
