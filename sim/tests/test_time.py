"""Tests for the pause-aware fixed-step clock."""

from sim.components import GameClock
from sim.time.game_clock import advance_clock


def test_accumulates_normal_frames_into_ticks():
    clock = GameClock(paused=False, time_scale=1.0)
    fixed_step = 1.0 / 30.0

    total = sum(advance_clock(clock, 1.0 / 60.0, fixed_step) for _ in range(10))

    assert total == 5           # 10 frames at 60 fps = 5 ticks at 30 Hz
    assert clock.tick == 5
    assert clock.accumulator < fixed_step


def test_paused_clock_does_not_advance():
    clock = GameClock(paused=True)

    assert advance_clock(clock, 10.0, 1.0 / 30.0) == 0
    assert clock.tick == 0


def test_long_stall_is_capped_instead_of_building_a_backlog():
    """A stalled frame must not make the next frame try to catch up forever."""
    clock = GameClock(paused=False, time_scale=1.0)

    ticks = advance_clock(clock, 10.0, 1.0 / 30.0, max_ticks=5)

    assert ticks == 5
    assert clock.tick == 5
    assert clock.accumulator < 1.0 / 30.0


def test_time_scale_never_exceeds_the_per_frame_cap():
    clock = GameClock(paused=False, time_scale=4.0)

    ticks = advance_clock(clock, 1.0, 1.0 / 30.0, max_ticks=5)

    assert ticks <= 5
