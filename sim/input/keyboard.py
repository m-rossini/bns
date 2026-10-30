"""Keyboard input handler for state transitions.

Maps physical key presses to logical state changes on GameSession.
"""

import time

from sim.components import GameSession, GameState


class KeyboardInput:
    def __init__(self, session: GameSession):
        self.session = session

    def handle_keypress(self, key: int) -> None:
        """Handle a key press and mutate session state accordingly."""
        session = self.session
        state = session.state

        if state == GameState.START:
            if key == 32:  # SPACE
                session.state = GameState.PLAYING
                session.clock.paused = False
                session.start_time = time.time()
            elif key == 271:  # Esc
                session.state = GameState.END
                session.end_reason = "user quit"

        elif state == GameState.PLAYING:
            if key == 32:  # SPACE
                pass  # reserved for future actions
            elif key == 80 or key == 271:  # P or Esc
                session.state = GameState.PAUSED
                session.clock.paused = True
            elif key == 81:  # Q
                session.state = GameState.END
                session.end_reason = "user quit"

        elif state == GameState.PAUSED:
            if key == 80 or key == 271:  # P or Esc
                session.state = GameState.PLAYING
                session.clock.paused = False
            elif key == 81:  # Q
                session.state = GameState.END
                session.end_reason = "user quit"

        elif state == GameState.END:
            if key == 32:  # SPACE
                self._restart(session)

    def _restart(self, session: GameSession) -> None:
        session.state = GameState.START
        session.clock = session.clock.__class__()  # fresh clock
        session.end_reason = None
        session.start_time = 0.0
        session.pause_time = 0.0
        if session.environment is not None:
            session.environment.reset()
