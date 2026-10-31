"""Pause-aware clock logic.

Decouples render frame rate from simulation tick rate using a fixed-step
accumulator. When paused, simulation time does not advance.

`time_scale` changes *perception* only: it slows or speeds how fast simulated
time seems to pass without changing ``tick_rate`` or the fixed-step tick
accumulation. Clamping keeps it inside `[time_scale_min, time_scale_max]`.
"""

from sim.components import GameClock


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def advance_clock(clock: GameClock, real_dt: float, fixed_step: float) -> int:
    """Advance the clock by real_dt seconds of wall time.

    Returns the number of simulation ticks executed this frame.
    """
    clock.real_dt = real_dt
    clock.sim_dt = 0.0

    if clock.paused:
        return 0

    # Accumulate scaled simulation time. time_scale only affects perception:
    # the fixed step (tick_rate) is unchanged.
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


def set_time_scale(clock: GameClock, value: float, vmin: float = 0.0,
                   vmax: float = 4.0) -> float:
    """Set the playback time scale, clamped to [vmin, vmax].

    Returns the value actually applied.
    """
    clock.time_scale = max(vmin, min(vmax, value))
    return clock.time_scale


def initial_time_scale(config_time_scale: float,
                       vmin: float = 0.0,
                       vmax: float = 4.0) -> float:
    """The configured playback scale, clamped to its allowed range."""
    return max(vmin, min(vmax, config_time_scale))
