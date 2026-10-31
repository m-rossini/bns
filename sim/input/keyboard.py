"""Keyboard input handler for state transitions.

Maps physical key presses to logical state changes on GameSession.

Key codes are pyglet/GLFW codes, not ASCII: letters are lowercase ASCII
(`P` = 112, `Q` = 113) and `Escape` is 65307.

Every transition is logged as a business event (`event=session.*`), so a run
can be replayed from its log: start, pause, resume, restart, quit.
"""

import logging
import time

from sim.components import GameSession, GameState
from sim.observability import get_logger, log_event

logger = get_logger("input")

KEY_SPACE = 32
KEY_P = 112
KEY_Q = 113
KEY_ESCAPE = 65307


def _emit(session: GameSession, event: str, level: int = logging.INFO, **fields) -> None:
    log_event(
        logger,
        event,
        level=level,
        tick=session.clock.tick,
        state=session.state.name,
        **fields,
    )


class KeyboardInput:
    def __init__(self, session: GameSession):
        self.session = session

    def handle_keypress(self, key: int) -> None:
        """Handle a key press and mutate session state accordingly."""
        session = self.session
        state = session.state

        if state == GameState.START:
            if key == KEY_SPACE:
                session.state = GameState.PLAYING
                session.clock.paused = False
                session.start_time = time.time()
                _emit(session, "session.started", key=key)
            elif key == KEY_P:
                session.state = GameState.PAUSED
                session.clock.paused = True
                _emit(session, "session.paused", key=key)
            elif key == KEY_ESCAPE:
                self._quit(session)
            else:
                _emit(session, "session.key_ignored", key=key, level=logging.DEBUG)

        elif state == GameState.PLAYING:
            if key in (KEY_P,):
                session.state = GameState.PAUSED
                session.clock.paused = True
                _emit(session, "session.paused", key=key)
            elif key in (KEY_Q, KEY_ESCAPE):
                self._quit(session)
            else:
                _emit(session, "session.key_ignored", key=key, level=logging.DEBUG)

        elif state == GameState.PAUSED:
            if key == KEY_P:
                session.state = GameState.PLAYING
                session.clock.paused = False
                _emit(session, "session.resumed", key=key)
            elif key in (KEY_Q, KEY_ESCAPE):
                self._quit(session)
            else:
                _emit(session, "session.key_ignored", key=key, level=logging.DEBUG)

        elif state == GameState.END:
            if key == KEY_SPACE:
                self._restart(session)
            elif key in (KEY_ESCAPE, KEY_Q):
                _emit(session, "session.closed", key=key)
                session.exit_requested = True

    @staticmethod
    def _quit(session: GameSession) -> None:
        session.state = GameState.END
        session.end_reason = "user quit"
        session.exit_requested = True
        _emit(session, "session.quit", reason=session.end_reason)

    def _restart(self, session: GameSession) -> None:
        _emit(session, "session.restart", previous_reason=session.end_reason)
        session.state = GameState.START
        session.clock = session.clock.__class__()  # fresh clock
        session.end_reason = None
        session.exit_requested = False
        session.start_time = 0.0
        session.pause_time = 0.0
        if session.environment is not None:
            session.environment.reset()
