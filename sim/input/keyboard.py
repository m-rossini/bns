"""Keyboard input handler for state transitions.

Maps physical key presses to logical state changes on GameSession.

Key codes are pyglet/GLFW codes, not ASCII: letters are lowercase ASCII
(`P` = 112, `Q` = 113) and `Escape` is 65307.
"""

import time

from sim.components import GameSession, GameState

KEY_SPACE = 32
KEY_P = 112
KEY_Q = 113
KEY_ESCAPE = 65307


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
            elif key == KEY_P:
                session.state = GameState.PAUSED
                session.clock.paused = True
            elif key == KEY_ESCAPE:
                self._quit(session)

        elif state == GameState.PLAYING:
            if key in (KEY_P,):
                session.state = GameState.PAUSED
                session.clock.paused = True
            elif key in (KEY_Q, KEY_ESCAPE):
                self._quit(session)

        elif state == GameState.PAUSED:
            if key == KEY_P:
                session.state = GameState.PLAYING
                session.clock.paused = False
            elif key in (KEY_Q, KEY_ESCAPE):
                self._quit(session)

        elif state == GameState.END:
            if key == KEY_SPACE:
                self._restart(session)
            elif key in (KEY_ESCAPE, KEY_Q):
                session.exit_requested = True

    @staticmethod
    def _quit(session: GameSession) -> None:
        session.state = GameState.END
        session.end_reason = "user quit"
        session.exit_requested = True

    def _restart(self, session: GameSession) -> None:
        session.state = GameState.START
        session.clock = session.clock.__class__()  # fresh clock
        session.end_reason = None
        session.exit_requested = False
        session.start_time = 0.0
        session.pause_time = 0.0
        if session.environment is not None:
            session.environment.reset()
