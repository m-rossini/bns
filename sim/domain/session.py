"""GameSession: top-level logical state container.

Holds the current GameState, World, Environment, GameClock, and metadata.
Only GameSession may change state.
"""

from typing import Optional

from sim.components import GameClock, GameSession as _GameSession, GameState
from sim.domain.environment import Environment
from sim.domain.world import World


class GameSession(_GameSession):
    """Concrete GameSession with typed world/environment."""

    def __init__(
        self,
        state: GameState = GameState.START,
        world: Optional[World] = None,
        environment: Optional[Environment] = None,
        clock: Optional[GameClock] = None,
        start_time: float = 0.0,
        pause_time: float = 0.0,
        end_reason: Optional[str] = None,
    ):
        super().__init__(
            state=state,
            world=world,
            environment=environment,
            clock=clock or GameClock(),
            start_time=start_time,
            pause_time=pause_time,
            end_reason=end_reason,
        )
