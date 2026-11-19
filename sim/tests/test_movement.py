"""Tests for bean movement strategies and the per-tick integration."""

import logging
import math
from dataclasses import replace

import pytest

from sim.components import Barrier, GameClock, GameSession, GameState
from sim.config import FoodConfig, MovementConfig
from sim.domain.beans import Bean
from sim.domain.genotype import DEFAULT_GENOTYPE, create_default_phenotype
from sim.domain.world import World
from sim.implementations.movement import StraightLineMovementStrategy
from sim.main import _step


def _food_strategy():
    """A real food strategy for step tests (food itself is not under test)."""
    from sim.implementations.food import RandomFoodSpawnStrategy

    return RandomFoodSpawnStrategy(FoodConfig())


def _world(width=200.0, height=200.0) -> World:
    return World(width=width, height=height, cell_size=10.0)


def _bean(bean_id=1, x=100.0, y=100.0) -> Bean:
    return Bean(id=bean_id, x=x, y=y, gender="male", color=(0, 0, 255))


def _resting_config(**overrides):
    values = dict(
        speed=60.0,
        direction=(1.0, 0.0),
        random_initial_direction=False,
        rest_speed_fraction=0.5,
    )
    values.update(overrides)
    return MovementConfig(**values)


class _StubEnv:
    """Fixed light/temperature readings for movement pacing tests."""

    def __init__(self, light: float, temperature: float):
        self._light = light
        self._temperature = temperature

    def light_at(self, x: float, y: float) -> float:
        return self._light

    def temperature_at(self, x: float, y: float) -> float:
        return self._temperature


def _rested_bean(bean_id=1, speed=60.0, resilience=0.0, energy_share=1.0):
    """Bean with an energy genotype; speed is the starting velocity."""
    genotype = replace(
        DEFAULT_GENOTYPE, acceleration=30.0, dawn_resilience=resilience,
        energy_capacity=1e12,
    )
    phenotype = create_default_phenotype(genotype)
    phenotype.current_speed = speed
    phenotype.velocity = (speed, 0.0)
    phenotype.current_energy = genotype.energy_capacity * energy_share
    return Bean(
        id=bean_id, x=100.0, y=100.0, gender="male", color=(0, 0, 255),
        vx=float(speed), vy=0.0, genotype=genotype, phenotype=phenotype,
    )


def test_night_eases_speed_down_gradually():
    """Darkness eases beans down toward half cruise in bounded steps."""
    world = _world(width=1000.0, height=1000.0)
    bean = _rested_bean(bean_id=1)
    strategy = StraightLineMovementStrategy(
        _resting_config(), bean_radius=5.0
    )
    night = _StubEnv(light=0.0, temperature=20.0)
    dt = 0.1  # acceleration budget: 30 * 0.1 = 3.0 per tick

    speeds = []
    for _ in range(12):
        strategy.update([bean], world, dt=dt, environment=night)
        speeds.append(math.hypot(bean.vx, bean.vy))

    assert speeds[0] < 60.0
    assert speeds[0] >= 60.0 - 3.0 - 1e-9  # one bounded step, no jump
    for before, after in zip(speeds, speeds[1:]):
        assert after <= before + 1e-9
        assert before - after <= 3.0 + 1e-9
    assert speeds[-1] == pytest.approx(30.0)


def test_warm_day_holds_cruise_speed():
    """Bright warm light keeps beans at full cruise."""
    world = _world(width=1000.0, height=1000.0)
    bean = _rested_bean(bean_id=1)
    strategy = StraightLineMovementStrategy(
        _resting_config(), bean_radius=5.0
    )
    day = _StubEnv(light=1.0, temperature=20.0)

    strategy.update([bean], world, dt=0.1, environment=day)

    assert math.hypot(bean.vx, bean.vy) == pytest.approx(60.0)


def test_cold_slows_beans_despite_daylight():
    """Cold is the binding constraint: bright but freezing means rest pace."""
    world = _world(width=1000.0, height=1000.0)
    bean = _rested_bean(bean_id=1)
    strategy = StraightLineMovementStrategy(
        _resting_config(), bean_radius=5.0
    )
    cold_day = _StubEnv(light=1.0, temperature=0.0)
    dt = 0.1

    speeds = []
    for _ in range(12):
        strategy.update([bean], world, dt=dt, environment=cold_day)
        speeds.append(math.hypot(bean.vx, bean.vy))

    assert speeds[-1] == pytest.approx(30.0)


def test_wake_up_accelerates_gradually():
    """Dawn eases beans back to cruise in bounded steps, never jumping."""
    world = _world(width=1000.0, height=1000.0)
    bean = _rested_bean(bean_id=1, speed=30.0)
    strategy = StraightLineMovementStrategy(
        _resting_config(), bean_radius=5.0
    )
    day = _StubEnv(light=1.0, temperature=20.0)
    dt = 0.1

    speeds = []
    for _ in range(12):
        strategy.update([bean], world, dt=dt, environment=day)
        speeds.append(math.hypot(bean.vx, bean.vy))

    assert speeds[0] > 30.0
    assert speeds[0] <= 30.0 + 3.0 + 1e-9
    for before, after in zip(speeds, speeds[1:]):
        assert after >= before - 1e-9
        assert after - before <= 3.0 + 1e-9
    assert speeds[-1] == pytest.approx(60.0)


def test_no_environment_means_cruise():
    """Without readings (unit tests) beans hold cruise speed."""
    world = _world(width=1000.0, height=1000.0)
    bean = _rested_bean(bean_id=1)
    strategy = StraightLineMovementStrategy(
        _resting_config(), bean_radius=5.0
    )

    strategy.update([bean], world, dt=0.1)

    assert math.hypot(bean.vx, bean.vy) == pytest.approx(60.0)


def test_resilient_beans_keep_sleeping_past_dawn():
    """At moderate morning light a deep sleeper targets less than a light one."""
    strategy = StraightLineMovementStrategy(
        _resting_config(), bean_radius=5.0
    )
    dawn = _StubEnv(light=0.7, temperature=20.0)

    light_sleeper = _rested_bean(bean_id=1, resilience=0.0)
    deep_sleeper = _rested_bean(bean_id=2, resilience=1.0)

    assert strategy._target_speed(light_sleeper, dawn) == pytest.approx(60.0)
    # day mark shifts 0.60 -> 0.90: vigor (0.7-0.1)/0.8 = 0.75.
    assert strategy._target_speed(deep_sleeper, dawn) == pytest.approx(52.5)


def test_heat_slows_beans_despite_bright_light():
    """A hot midday forces siesta pace even at full daylight."""
    strategy = StraightLineMovementStrategy(
        _resting_config(), bean_radius=5.0
    )
    heatwave = _StubEnv(light=1.0, temperature=35.0)
    bean = _rested_bean(bean_id=1)

    # heat vigor (38-35)/10 = 0.3 -> 60 * (0.5 + 0.5 * 0.3).
    assert strategy._target_speed(bean, heatwave) == pytest.approx(39.0)


def test_hunger_deepens_sleep():
    """Same dawn, same genes: the emptier bean targets a slower pace."""
    strategy = StraightLineMovementStrategy(
        _resting_config(), bean_radius=5.0
    )
    dawn = _StubEnv(light=0.7, temperature=20.0)

    full = _rested_bean(bean_id=1, energy_share=1.0)
    hungry = _rested_bean(bean_id=2, energy_share=0.1)

    assert strategy._target_speed(full, dawn) == pytest.approx(60.0)
    # vigor 1.0 scaled by 0.6 + 0.4 * 0.1 = 0.64.
    assert strategy._target_speed(hungry, dawn) == pytest.approx(60.0 * (0.5 + 0.5 * 0.64))


def test_rest_config_validation():
    """The rest fraction must slow beans down without stopping them."""
    with pytest.raises(ValueError):
        MovementConfig(rest_speed_fraction=0.0)
    with pytest.raises(ValueError):
        MovementConfig(rest_speed_fraction=1.5)


def test_bean_moves_in_place_along_the_global_direction():
    world = _world()
    bean = _bean()
    strategy = StraightLineMovementStrategy(
        MovementConfig(speed=10.0, direction=(1.0, 0.0), random_initial_direction=False), bean_radius=5.0
    )

    strategy.update([bean], world, dt=1.0)

    assert bean.x == 110.0
    assert bean.y == 100.0
    assert bean.vx == 10.0
    assert bean.vy == 0.0
    assert bean.position == (110.0, 100.0)


def test_bean_bounces_off_the_right_edge_and_keeps_its_id(caplog):
    world = _world(width=100.0, height=100.0)
    bean = _bean(x=94.0, y=50.0)
    original = bean
    strategy = StraightLineMovementStrategy(
        MovementConfig(speed=10.0, direction=(1.0, 0.0), random_initial_direction=False), bean_radius=5.0
    )

    with caplog.at_level(logging.DEBUG, logger="bean.movement.straight_line"):
        strategy.update([bean], world, dt=1.0)

    assert bean is original
    assert bean.id == 1
    assert bean.x == 86.0          # 94 + 10 = 104; reflect around 95 => 86
    assert bean.vx == -10.0
    assert "event=bean.bounced" in caplog.text
    assert all(r.levelno == logging.DEBUG for r in caplog.records)


def test_beans_keep_independent_velocities_after_bouncing():
    world = _world(width=100.0, height=100.0)
    left = _bean(bean_id=1, x=20.0, y=50.0)
    right = _bean(bean_id=2, x=94.0, y=50.0)
    strategy = StraightLineMovementStrategy(
        MovementConfig(speed=10.0, direction=(1.0, 0.0), random_initial_direction=False), bean_radius=5.0
    )

    strategy.update([left, right], world, dt=1.0)

    assert left.vx == 10.0
    assert right.vx == -10.0


def test_bean_barrier_collision_is_logged(caplog):
    world = _world()
    world.add_barrier(
        Barrier(id=7, kind="rect", x=90.0, y=90.0, width=30.0, height=30.0)
    )
    bean = _bean(x=100.0, y=100.0)
    strategy = StraightLineMovementStrategy(
        MovementConfig(speed=0.0, direction=(1.0, 0.0), random_initial_direction=False), bean_radius=5.0
    )

    with caplog.at_level(logging.DEBUG, logger="bean.movement.straight_line"):
        strategy.update([bean], world, dt=1.0)

    assert "event=bean.collided_barrier" in caplog.text
    assert "barrier_id=7" in caplog.text
    assert all(r.levelno == logging.DEBUG for r in caplog.records)


def test_bean_bean_collision_is_logged(caplog):
    world = _world()
    first = _bean(bean_id=1, x=100.0, y=100.0)
    second = _bean(bean_id=2, x=101.0, y=100.0)
    strategy = StraightLineMovementStrategy(
        MovementConfig(speed=0.0, direction=(1.0, 0.0), random_initial_direction=False), bean_radius=5.0
    )

    with caplog.at_level(logging.DEBUG, logger="bean.movement.straight_line"):
        strategy.update([first, second], world, dt=1.0)

    assert "event=bean.collided_bean" in caplog.text
    assert "bean_id=1" in caplog.text
    assert "other_id=2" in caplog.text
    assert all(r.levelno == logging.DEBUG for r in caplog.records)


def test_collision_work_is_skipped_when_debug_is_off(caplog):
    """Collision detection only feeds DEBUG logs, so INFO must skip it."""
    world = _world()
    world.add_barrier(
        Barrier(id=7, kind="rect", x=90.0, y=90.0, width=30.0, height=30.0)
    )
    beans = [_bean(bean_id=1, x=100.0, y=100.0), _bean(bean_id=2, x=101.0, y=100.0)]
    strategy = StraightLineMovementStrategy(
        MovementConfig(speed=0.0, direction=(1.0, 0.0), random_initial_direction=False), bean_radius=5.0
    )

    with caplog.at_level(logging.INFO, logger="bean.movement.straight_line"):
        strategy.update(beans, world, dt=1.0)

    assert caplog.records == []


def test_numba_collisions_degrade_without_numpy(monkeypatch):
    """A missing numpy disables the fast path instead of crashing the import."""
    import importlib
    import sys

    import sim.implementations.movement.numba_collisions as nc

    monkeypatch.setitem(sys.modules, "numpy", None)
    reloaded = importlib.reload(nc)
    try:
        assert reloaded.NUMPY_AVAILABLE is False
        assert reloaded.NUMBA_AVAILABLE is False
        assert reloaded.check_barrier_collisions_numba([], [], 1.0) == []
        assert reloaded.check_bean_collisions_numba([], 1.0, 100.0, 100.0) == []
    finally:
        monkeypatch.undo()
        importlib.reload(nc)


def test_step_moves_beans_only_while_playing():
    world = _world()
    bean = _bean(x=50.0, y=50.0)
    session = GameSession(state=GameState.PLAYING, world=world)
    session.beans = [bean]
    session.clock = GameClock(paused=False)
    strategy = StraightLineMovementStrategy(
        MovementConfig(speed=10.0, direction=(1.0, 0.0), random_initial_direction=False), bean_radius=5.0
    )
    fixed_step = 1.0

    _step(session, None, strategy, None, real_dt=fixed_step, fixed_step=fixed_step,
          food_strategy=_food_strategy())
    assert bean.x == 60.0

    session.state = GameState.PAUSED
    session.clock.paused = True
    _step(session, None, strategy, None, real_dt=fixed_step, fixed_step=fixed_step,
          food_strategy=_food_strategy())
    assert bean.x == 60.0
