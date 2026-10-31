"""Interface for barrier strategies.

A barrier strategy owns the rules that shape static obstacles:

* the fill colour every barrier uses (default yellow);
* the maximum span, in grid cells, a barrier may cover in either direction
  (3 means 3x3, 3x1, 1x2 are valid and 4x1 is not);
* the deterministic placement of the barriers in the world.

The world delegates validation to the strategy, so swapping the strategy
swaps the rules without touching `World`.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple

from sim.components import Barrier
from sim.interfaces.world import IWorld

Color = Tuple[int, int, int]


class IBarrierStrategy(ABC):
    @property
    @abstractmethod
    def color(self) -> Color:
        """Fill colour used for every barrier (default yellow)."""

    @property
    @abstractmethod
    def max_span_cells(self) -> int:
        """Maximum number of grid cells a barrier may span per direction."""

    @abstractmethod
    def span_cells(self, barrier: Barrier, world: IWorld) -> Tuple[int, int]:
        """(columns, rows) the barrier occupies, rounded up to whole cells."""

    @abstractmethod
    def validate(self, barrier: Barrier, world: IWorld) -> None:
        """Raise ``ValueError`` when the barrier breaks the strategy's rules."""

    @abstractmethod
    def create_barriers(self, world: IWorld) -> List[Barrier]:
        """Deterministically generate the configured set of barriers."""
