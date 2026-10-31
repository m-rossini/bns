"""Interface for the logical world.

The world owns the bounded arena, its cell grid, orientation and wrap
behavior. It knows nothing about rendering or beans.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Tuple

from sim.components import Barrier

if TYPE_CHECKING:  # pragma: no cover - typing only (avoids an import cycle)
    from sim.interfaces.barrier import IBarrierStrategy


class IWorld(ABC):
    @property
    @abstractmethod
    def width(self) -> float:
        ...

    @property
    @abstractmethod
    def height(self) -> float:
        ...

    @property
    @abstractmethod
    def cell_size(self) -> float:
        ...

    @property
    @abstractmethod
    def cols(self) -> int:
        ...

    @property
    @abstractmethod
    def rows(self) -> int:
        ...

    @property
    @abstractmethod
    def orientation(self) -> str:
        ...

    @property
    @abstractmethod
    def wrap_around(self) -> bool:
        ...

    @property
    @abstractmethod
    def barriers(self) -> List[Barrier]:
        ...

    @property
    @abstractmethod
    def barrier_strategy(self) -> Optional["IBarrierStrategy"]:
        ...

    @abstractmethod
    def set_barrier_strategy(
        self, strategy: Optional["IBarrierStrategy"]
    ) -> None:
        ...

    @abstractmethod
    def add_barrier(self, barrier: Barrier) -> None:
        ...

    @abstractmethod
    def remove_barrier(self, barrier_id: int) -> bool:
        ...

    @abstractmethod
    def cell_index(self, x: float, y: float) -> Tuple[int, int]:
        ...

    @abstractmethod
    def cell_center(self, col: int, row: int) -> Tuple[float, float]:
        ...

    @abstractmethod
    def cell_bounds(self, col: int, row: int) -> Tuple[float, float, float, float]:
        ...

    @abstractmethod
    def is_inside(self, x: float, y: float) -> bool:
        ...

    @abstractmethod
    def clamp_or_wrap(self, x: float, y: float) -> Tuple[float, float]:
        ...
