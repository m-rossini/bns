"""Pure-Python configuration for the bean simulation.

No YAML/JSON. All tunable values live here as dataclasses.
"""

from dataclasses import dataclass, field
from typing import List, Literal, Optional


@dataclass
class BarrierConfig:
    id: int
    kind: Literal["rect", "circle"]
    x: float
    y: float
    width: float = 0.0
    height: float = 0.0
    radius: float = 0.0


@dataclass
class WorldConfig:
    width: float = 1200.0
    height: float = 800.0
    orientation: Literal["north_south", "east_west", "square"] = "north_south"
    wrap_around: bool = False
    barriers: List[BarrierConfig] = field(default_factory=list)


@dataclass
class EnvironmentConfig:
    """Strategy class names are resolved by the DI container.

    Transition ticks (day length, season length, storm frequency) live
    inside each strategy's own config, not here.
    """
    weather_strategy: Optional[str] = None
    season_strategy: Optional[str] = None
    daynight_strategy: Optional[str] = None


@dataclass
class SimulationConfig:
    world: WorldConfig = field(default_factory=WorldConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    debug: bool = False
    tick_rate: float = 30.0  # simulation ticks per second
