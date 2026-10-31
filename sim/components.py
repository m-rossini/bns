"""Core data components for the simulation.

Plain dataclasses with no behavior. Systems and domain objects hold logic.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple


@dataclass
class Bean:
    """A unicellular organism placed in the world by the spawn controller.

    ``gender`` and ``color`` come from the gender controller; visual
    rendering draws a small cross in this color at ``(x, y)``.
    """

    id: int
    x: float
    y: float
    gender: str
    color: Tuple[int, int, int]

    @property
    def position(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Barrier:
    """A static obstacle in the world.

    Coordinates and sizes are world units. ``color`` is copied from the
    barrier strategy that created it, so the renderer never hardcodes one.
    """

    id: int
    kind: str  # "rect" or "circle"
    x: float
    y: float
    width: float = 0.0
    height: float = 0.0
    radius: float = 0.0
    color: Tuple[int, int, int] = (255, 208, 64)


class GameState(Enum):
    START = auto()    # Title screen, press to begin
    PLAYING = auto()  # Simulation running, time passing
    PAUSED = auto()   # Simulation frozen, overlay shown
    END = auto()      # Game over / population extinct / user quit


@dataclass
class GameClock:
    """Pause-aware clock that decouples render frames from simulation ticks.

    real_dt: seconds elapsed since last frame (wall clock).
    sim_dt:   seconds advanced in the simulation this frame (0 when paused).
    accumulator: leftover time for fixed tick steps.
    tick:    number of simulation ticks completed.
    paused:  whether the simulation clock is stopped (starts paused on the
             title screen; START -> PLAYING unpauses it).
    time_scale: multiplier for sim time (1.0 normal, 2.0 fast-forward, etc.).
    """
    real_dt: float = 0.0
    sim_dt: float = 0.0
    accumulator: float = 0.0
    tick: int = 0
    paused: bool = True
    time_scale: float = 1.0


@dataclass
class GameSession:
    """Owns the top-level logical state of the game.

    Only GameSession may change state. Systems query session.state
    before running.
    """
    state: GameState = GameState.START
    world: Optional["World"] = None
    environment: Optional["Environment"] = None
    clock: GameClock = field(default_factory=GameClock)
    start_time: float = 0.0      # real timestamp when session began
    pause_time: float = 0.0      # accumulated paused duration
    end_reason: Optional[str] = None
    exit_requested: bool = False  # set by input; the app loop closes the window
    beans: List[Bean] = field(default_factory=list)   # spawned beans
