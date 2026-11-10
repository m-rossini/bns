"""Tests for bean movement strategies and the per-tick integration."""

import logging

from sim.components import Barrier, GameClock, GameSession, GameState
from sim.config import MovementConfig
from sim.domain.beans import Bean
from sim.domain.world import World
from sim.implementations.movement import StraightLineMovementStrategy
from sim.main import _step


def _world(width=200.0, height=200.0) -> World:
    return World(width=width, height=height, cell_size=10.0)


def _bean(bean_id=1, x=100.0, y=100.0) -> Bean:
    return Bean(id=bean_id, x=x, y=y, gender="male", color=(0, 0, 255))


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

    _step(session, None, strategy, None, real_dt=fixed_step, fixed_step=fixed_step)
    assert bean.x == 60.0

    session.state = GameState.PAUSED
    session.clock.paused = True
    _step(session, None, strategy, None, real_dt=fixed_step, fixed_step=fixed_step)
    assert bean.x == 60.0
