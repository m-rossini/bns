"""Concrete World implementation.

Holds the bounded arena, its cell grid, orientation and wrap behavior.

World units are the only spatial unit. Cells are derived from `cell_size`;
the view applies its own world -> screen scale, so nothing here knows about
pixels or window sizes.
"""

from typing import List, Optional, Tuple

from sim.components import Barrier
from sim.interfaces.world import IWorld


class World(IWorld):
    def __init__(
        self,
        width: float,
        height: float,
        cell_size: float = 50.0,
        orientation: str = "north_south",
        wrap_around: bool = False,
    ):
        if width <= 0 or height <= 0:
            raise ValueError("World width and height must be positive")
        if cell_size <= 0:
            raise ValueError("World cell_size must be positive")
        self._width = width
        self._height = height
        self._cell_size = cell_size
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
    def cell_size(self) -> float:
        return self._cell_size

    @property
    def cols(self) -> int:
        return max(1, int(round(self._width / self._cell_size)))

    @property
    def rows(self) -> int:
        return max(1, int(round(self._height / self._cell_size)))

    @property
    def orientation(self) -> str:
        return self._orientation

    @property
    def wrap_around(self) -> bool:
        return self._wrap_around

    # ------------------------------------------------------------------
    # Cells
    # ------------------------------------------------------------------
    def cell_index(self, x: float, y: float) -> Tuple[int, int]:
        """World position -> (column, row), clamped to the grid."""
        col = int(x // self._cell_size)
        row = int(y // self._cell_size)
        col = max(0, min(self.cols - 1, col))
        row = max(0, min(self.rows - 1, row))
        return col, row

    def cell_center(self, col: int, row: int) -> Tuple[float, float]:
        return (
            (col + 0.5) * self._cell_size,
            (row + 0.5) * self._cell_size,
        )

    def cell_bounds(self, col: int, row: int) -> Tuple[float, float, float, float]:
        """(left, bottom, width, height) of a cell in world units."""
        return (
            col * self._cell_size,
            row * self._cell_size,
            self._cell_size,
            self._cell_size,
        )

    # ------------------------------------------------------------------
    # Barriers (kept for a future object/collision pass; unused today)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Bounds
    # ------------------------------------------------------------------
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
