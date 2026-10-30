"""Concrete World implementation.

Holds arena bounds, orientation, wrap behavior, and static barriers.
"""

from typing import List, Optional, Tuple

from sim.components import Barrier, GameClock
from sim.interfaces.environment import IEnvironment
from sim.interfaces.world import IWorld


class World(IWorld):
    def __init__(
        self,
        width: float,
        height: float,
        orientation: str = "north_south",
        wrap_around: bool = False,
    ):
        if width <= 0 or height <= 0:
            raise ValueError("World width and height must be positive")
        self._width = width
        self._height = height
        self._orientation = orientation
        self._wrap_around = wrap_around
        self._barriers: List[Barrier] = []

    @property
    def width(self) -> float:
        return self._width

    @property
    def height(self) -> float:
        return self._height

    @property
    def orientation(self) -> str:
        return self._orientation

    @property
    def wrap_around(self) -> bool:
        return self._wrap_around

    @property
    def barriers(self) -> List[Barrier]:
        return list(self._barriers)

    def add_barrier(self, barrier: Barrier) -> None:
        if any(b.id == barrier.id for b in self._barriers):
            raise ValueError(f"Barrier id {barrier.id} already exists")
        self._barriers.append(barrier)

    def remove_barrier(self, barrier_id: int) -> bool:
        for i, b in enumerate(self._barriers):
            if b.id == barrier_id:
                self._barriers.pop(i)
                return True
        return False

    def is_inside(self, x: float, y: float) -> bool:
        return 0.0 <= x <= self._width and 0.0 <= y <= self._height

    def clamp_or_wrap(self, x: float, y: float) -> Tuple[float, float]:
        if self._wrap_around:
            x = x % self._width
            y = y % self._height
        else:
            x = max(0.0, min(self._width, x))
            y = max(0.0, min(self._height, y))
        return x, y
