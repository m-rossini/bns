"""Entry point for the bean simulation.

Boots the DI container, creates the Arcade view, and runs the main loop.
Time passage is pause-aware: simulation ticks only advance while PLAYING.

Set BEAN_HEADLESS=1 to run without a window. Headless mode never imports
Arcade/OpenGL, so it works in containers with no display server at all.
"""

import os
import time

from sim.components import GameSession, GameState
from sim.config import DEFAULT_CONFIG
from sim.container import Container
from sim.domain.environment import Environment
from sim.input.keyboard import KeyboardInput
from sim.time.game_clock import advance_clock


def _step(
    session: GameSession,
    environment: Environment | None,
    real_dt: float,
    fixed_step: float,
) -> int:
    """Advance the pause-aware clock and every system that depends on it."""
    ticks_executed = advance_clock(session.clock, real_dt, fixed_step)

    # The environment advances once per simulation tick, so environment.tick
    # always tracks clock.tick.
    if ticks_executed > 0 and environment is not None:
        for _ in range(ticks_executed):
            environment.advance_tick()

    # Run simulation systems only when PLAYING
    if session.state == GameState.PLAYING:
        # Placeholder for bean/movement/collision systems
        pass

    return ticks_executed


def run_headless(
    session: GameSession,
    environment: Environment | None,
    fixed_step: float,
) -> None:
    """Run a bounded number of deterministic frames without a window."""
    frames = int(os.environ.get("BEAN_HEADLESS_FRAMES", "600"))
    frame_dt = 1.0 / 60.0

    # There is no input in headless mode, so start the simulation directly.
    session.state = GameState.PLAYING
    session.clock.paused = False
    session.start_time = time.time()

    for _ in range(max(0, frames)):
        _step(session, environment, frame_dt, fixed_step)

    env_tick = environment.tick if environment is not None else 0
    if environment is not None:
        calendar = environment.calendar
        palette = environment.palette
        weather = environment.weather
        print(
            f"headless run finished: frames={frames} ticks={session.clock.tick} "
            f"env_tick={env_tick} day={calendar.day} clock={calendar.clock} "
            f"season={palette.name} weather={weather}",
            flush=True,
        )
    else:
        print(
            f"headless run finished: frames={frames} ticks={session.clock.tick}",
            flush=True,
        )


def main() -> None:
    config = DEFAULT_CONFIG
    container = Container(config)

    session = container.session
    environment = container.environment

    headless = os.environ.get("BEAN_HEADLESS", "0") == "1"
    fixed_step = 1.0 / config.tick_rate

    if headless:
        run_headless(session, environment, fixed_step)
        return

    # Import Arcade only for the windowed path; headless runs stay free of
    # OpenGL/display dependencies.
    import arcade

    from sim.rendering.arcade_view import ArcadeView

    view = ArcadeView(
        session,
        width=int(config.world.width) + 360,
        height=int(config.world.height),
        title="Bean World",
        tick_rate=config.tick_rate,
    )

    view.set_input_handler(KeyboardInput(session))

    last_time = time.perf_counter()

    def on_update(dt: float) -> None:
        nonlocal last_time
        now = time.perf_counter()
        real_dt = now - last_time
        last_time = now
        _step(session, environment, real_dt, fixed_step)

        if session.exit_requested:
            view.close()
            arcade.exit()

    view.on_update = on_update

    arcade.run()


if __name__ == "__main__":
    main()
