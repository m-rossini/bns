"""Bean domain objects.

A :class:`Bean` is a unicellular organism placed at initial simulation time
by the :class:`sim.domain.spawn_controller.SpawnController`. Each bean has a
world position, a gender identity, an associated visual color, and an
energy/genotype system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from sim.domain.genotype import Genotype, Phenotype

Color = Tuple[int, int, int]
Position = Tuple[float, float]


@dataclass(slots=True)
class Bean:
    """A unicellular organism placed in the world.

    ``gender`` and ``color`` come from the gender controller; visual
    rendering draws a small cross in this color at ``(x, y)``.

    Beans are mutable on purpose: the movement system updates ``x``/``y`` and
    the per-bean velocity in place, so thousands of beans are not recreated
    every tick. ``id`` is unique for the whole lifetime of the simulation.

    Energy/genotype system:
    - ``genotype``: immutable traits (capacity, metabolic rate, drag, etc.)
    - ``phenotype``: mutable state (current energy, speed, age, dormancy)
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
    #: Immutable genetic traits (set at birth)
    genotype: Optional[Genotype] = None
    #: Mutable phenotypic state (changes during simulation)
    phenotype: Optional[Phenotype] = None

    @property
    def position(self) -> Position:
        return (self.x, self.y)

    def is_dormant(self) -> bool:
        """Check if bean is dormant (energy depleted)."""
        return self.phenotype is not None and self.phenotype.is_dormant

    def update_color_from_phenotype(self) -> None:
        """Sync bean color with phenotype (for rendering)."""
        if self.phenotype is not None:
            self.color = self.phenotype.color


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
