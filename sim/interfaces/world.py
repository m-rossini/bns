"""Interface for the logical world.

The world owns the bounded arena, orientation, wrap behavior, and barriers.
It knows nothing about rendering or beans.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from sim.components import Barrier


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

    @abstractmethod
    def add_barrier(self, barrier: Barrier) -> None:
        ...

    @abstractmethod
    def remove_barrier(self, barrier_id: int) -> bool:
        ...

    @abstractmethod
    def is_inside(self, x: float, y: float) -> bool:
        ...

    @abstractmethod
    def clamp_or_wrap(self, x: float, y: float) -> Tuple[float, float]:
        ...
