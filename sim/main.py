"""Entry point for the bean simulation.

Boots the DI container, creates the Arcade view, and runs the main loop.
Time passage is pause-aware: simulation ticks only advance while PLAYING.

Set BEAN_HEADLESS=1 to run without a window. Headless mode never imports
Arcade/OpenGL, so it works in containers with no display server at all.

Logging is configured before anything else. The level comes from
``BEAN_LOG_LEVEL`` (exposed by the Makefile as ``LOG_LEVEL``) and falls back
to ``SimulationConfig.logging.level`` (default ``INFO``).
"""

import logging
import os
import time

from sim.components import GameSession, GameState
from sim.config import DEFAULT_CONFIG
from sim.container import Container
from sim.domain.environment import Environment
from sim.input.keyboard import KeyboardInput
from sim.observability import configure_logging, get_logger, log_event
from sim.time.game_clock import advance_clock, initial_time_scale, set_time_scale

logger = get_logger("main")


def _step(
    session: GameSession,
    environment: Environment | None,
    movement_strategy,
    energy_strategy,
    real_dt: float,
    fixed_step: float,
    max_ticks: int = 5,
) -> int:
    """Advance the pause-aware clock and every system that depends on it."""
    ticks_executed = advance_clock(
        session.clock, real_dt, fixed_step, max_ticks=max_ticks
    )

    # The environment advances once per simulation tick, so environment.tick
    # always tracks clock.tick. Bean movement runs on the same tick, but only
    # while the session is actually playing.
    for _ in range(ticks_executed):
        if environment is not None and session.state == GameState.PLAYING:
            environment.advance_tick()
        if (
            energy_strategy is not None
            and session.state == GameState.PLAYING
            and session.world is not None
        ):
            # Apply energy gains
            gains = energy_strategy.calculate_energy_gain(
                session.beans, environment, session.world, fixed_step
            )
            for bean in session.beans:
                if bean.phenotype is not None and bean.genotype is not None:
                    gain = gains.get(bean.id, 0.0)
                    if gain > 0:
                        from sim.domain.genotype import apply_energy_gain
                        apply_energy_gain(bean.phenotype, bean.genotype, gain)
                        bean.update_color_from_phenotype()

        if (
            movement_strategy is not None
            and session.state == GameState.PLAYING
            and session.world is not None
        ):
            movement_strategy.update(session.beans, session.world, fixed_step)

        # Check if all beans are dormant (energy depleted) - end simulation
        if session.state == GameState.PLAYING:
            alive_count = sum(
                1 for bean in session.beans
                if bean.phenotype is not None and not bean.phenotype.is_dormant
            )
            if alive_count == 0 and len(session.beans) > 0:
                session.state = GameState.END
                session.end_reason = "all_beans_dormant"
                log_event(
                    logger,
                    "session.all_beans_dormant",
                    ticks=session.clock.tick,
                    initial_population=len(session.beans),
                    initial_female=getattr(session, "initial_female", 0),
                    initial_male=getattr(session, "initial_male", 0),
                )

    return ticks_executed


def run_headless(
    session: GameSession,
    environment: Environment | None,
    movement_strategy,
    energy_strategy,
    fixed_step: float,
    max_ticks: int = 5,
) -> None:
    """Run a bounded number of deterministic frames without a window."""
    frames = int(os.environ.get("BEAN_HEADLESS_FRAMES", "600"))
    frame_dt = 1.0 / 60.0

    log_event(
        logger,
        "session.headless_started",
        frames=frames,
        tick_rate=1.0 / fixed_step,
        season=session.environment.season if session.environment else None,
    )

    # There is no input in headless mode, so start the simulation directly.
    session.state = GameState.PLAYING
    session.clock.paused = False
    session.start_time = time.time()

    for _ in range(max(0, frames)):
        _step(
            session, environment, movement_strategy, energy_strategy, frame_dt, fixed_step,
            max_ticks=max_ticks,
        )
        # Stop early if simulation ended (all beans dormant)
        if session.state == GameState.END:
            break

    env_tick = environment.tick if environment is not None else 0
    if environment is not None:
        calendar = environment.calendar
        palette = environment.palette
        log_event(
            logger,
            "session.headless_finished",
            frames=frames,
            ticks=session.clock.tick,
            env_tick=env_tick,
            day=calendar.day,
            clock=calendar.clock,
            season=palette.name,
            weather=environment.weather,
        )
    else:
        log_event(
            logger,
            "session.headless_finished",
            frames=frames,
            ticks=session.clock.tick,
            env_tick=env_tick,
        )


def main() -> None:
    config = DEFAULT_CONFIG
    level = configure_logging(config)

    log_event(
        logger,
        "app.start",
        log_level=level,
        headless=os.environ.get("BEAN_HEADLESS", "0") == "1",
        tick_rate=config.tick_rate,
        world=f"{config.world.width}x{config.world.height}",
        cell_size=config.world.cell_size,
        cols=config.world.cols,
        rows=config.world.rows,
    )

    try:
        container = Container(config)
    except Exception:
        logger.exception("app.crashed config.invalid")
        logging.shutdown()
        return

    session = container.session
    environment = container.environment
    movement_strategy = container.movement_strategy
    energy_strategy = container.energy_strategy

    headless = os.environ.get("BEAN_HEADLESS", "0") == "1"
    fixed_step = 1.0 / config.tick_rate
    max_ticks = config.time.max_ticks_per_frame

    # Initial playback scale from config; changes *perception* only, never the
    # fixed tick rate or sim time progression.
    session.clock.time_scale = initial_time_scale(
        config.time.initial_time_scale,
        vmin=config.time.time_scale_min,
        vmax=config.time.time_scale_max,
    )

    if headless:
        try:
            run_headless(
                session, environment, movement_strategy, energy_strategy, fixed_step,
                max_ticks=max_ticks,
            )
        except Exception:
            logger.exception("app.crashed mode=headless")
            raise
        finally:
            logging.shutdown()
        return

    # Import Arcade only for the windowed path; headless runs stay free of
    # OpenGL/display dependencies.
    import arcade

    from sim.rendering.arcade_view import ArcadeView

    # Preferred default window: 1:1 world rendering (1 world unit = 1 screen
    # pixel at default scale), plus a full-height sidebar. Integer-snapped so
    # cell rectangles land on whole pixels.
    _SIDEBAR_WIDTH = 360
    try:
        view = ArcadeView(
            session,
            width=_SIDEBAR_WIDTH + int(config.world.width),
            # World height plus top/bottom margins so the drawn world is 1:1
            # (scale 1.0) at startup.
            height=int(config.world.height) + 2 * 12,
            title="Bean World",
            tick_rate=config.tick_rate,
            sim_config=config,
        )
    except Exception:
        logger.exception("app.crashed view.init")
        logging.shutdown()
        return

    view.set_input_handler(KeyboardInput(session))

    last_time = time.perf_counter()

    def on_update(dt: float) -> None:
        nonlocal last_time
        now = time.perf_counter()
        real_dt = now - last_time
        last_time = now
        if session.state != GameState.END:
            _step(
                session, environment, movement_strategy, energy_strategy, real_dt, fixed_step,
                max_ticks=max_ticks,
            )

        if session.exit_requested:
            log_event(
                logger,
                "app.window_closing",
                ticks=session.clock.tick,
                reason=session.end_reason,
            )
            view.close()
            arcade.exit()
            view.close()
            arcade.exit()

    view.on_update = on_update

    log_event(
        logger,
        "app.window_created",
        width=view.width,
        height=view.height,
        resizable=True,
    )

    try:
        arcade.run()
    except Exception:
        logger.exception("app.crashed mode=windowed")
        raise
    finally:
        log_event(
            logger,
            "app.stop",
            ticks=session.clock.tick,
            state=session.state.name,
            reason=session.end_reason,
        )
        logging.shutdown()


if __name__ == "__main__":
    main()
