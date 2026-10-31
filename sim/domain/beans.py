"""Bean domain objects.

A :class:`Bean` is a unicellular organism placed at initial simulation time
by the :class:`sim.domain.spawn_controller.SpawnController`. Each bean has a
world position, a gender identity, and an associated visual color.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

Color = Tuple[int, int, int]
Position = Tuple[float, float]


@dataclass(frozen=True)
class Bean:
    """A unicellular organism placed in the world.

    ``gender`` and ``color`` come from the gender controller; visual
    rendering draws a small cross in this color at ``(x, y)``.
    """

    id: int
    x: float
    y: float
    gender: str
    color: Color

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
