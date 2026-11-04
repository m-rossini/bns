"""Bean domain objects.

A :class:`Bean` is a unicellular organism placed at initial simulation time
by the :class:`sim.domain.spawn_controller.SpawnController`. Each bean has a
world position, a gender identity, and an associated visual color.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

Color = Tuple[int, int, int]
Position = Tuple[float, float]


@dataclass
class Bean:
    """A unicellular organism placed in the world.

    ``gender`` and ``color`` come from the gender controller; visual
    rendering draws a small cross in this color at ``(x, y)``.

    Beans are mutable on purpose: the movement system updates ``x``/``y`` and
    the per-bean velocity in place, so thousands of beans are not recreated
    every tick. ``id`` is unique for the whole lifetime of the simulation.
    """

    id: int
    x: float
    y: float
    gender: str
    color: Color
    #: Per-bean velocity in world units per second. ``None`` until the first
    #: movement update seeds it from the movement strategy's global direction.
    vx: Optional[float] = None
    vy: Optional[float] = None

    @property
    def position(self) -> Position:
        return (self.x, self.y)


@dataclass(frozen=True)
class SpawnResult:
    """Outcome of a single bean spawn cycle."""

    beans: Tuple[Bean, ...]
    target_population: int
    actual_population: int
    world_area: float
    density_coefficient: float
    variance: float
    strategy_name: str
