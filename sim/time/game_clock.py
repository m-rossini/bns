"""Pause-aware clock logic.

Decouples render frame rate from simulation tick rate using a fixed-step
accumulator. When paused, simulation time does not advance.
"""

from sim.components import GameClock


def advance_clock(clock: GameClock, real_dt: float, fixed_step: float) -> int:
    """Advance the clock by real_dt seconds of wall time.

    Returns the number of simulation ticks executed this frame.
    """
    clock.real_dt = real_dt
    clock.sim_dt = 0.0

    if clock.paused:
        return 0

    # Accumulate scaled simulation time
    clock.accumulator += real_dt * clock.time_scale

    ticks_executed = 0
    while clock.accumulator >= fixed_step:
        clock.accumulator -= fixed_step
        clock.sim_dt += fixed_step
        clock.tick += 1
        ticks_executed += 1

    return ticks_executed


def pause(clock: GameClock) -> None:
    clock.paused = True


def resume(clock: GameClock) -> None:
    clock.paused = False


def toggle_pause(clock: GameClock) -> bool:
    clock.paused = not clock.paused
    return clock.paused
