"""Single source of truth for world <-> screen coordinate mapping.

`WorldLayout` owns the cell-grid geometry and the projection between world
units and screen (logical window) coordinates. Both hit-testing (mouse
motion/press) and drawing (grid, cells, markers) use this one layout so the
selected cell, the orange marker and the cursor always agree.

Coordinates live in **logical window coordinates**. On this platform
(``dpi_scaling="stretch"``, scale 1.0) logical coordinates equal framebuffer
pixels, so no viewport/scale conversion is needed; the layout is computed once
from the viewport size and reused by draw and hit-test alike.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from sim.interfaces.world import IWorld


@dataclass(frozen=True)
class WorldLayout:
    """Projection between world units and screen (logical) pixels."""

    left: float
    bottom: float
    scale: float
    cell_size: float
    cols: int
    rows: int
    world_width: float
    world_height: float

    @property
    def right(self) -> float:
        return self.left + self.world_width * self.scale

    @property
    def top(self) -> float:
        return self.bottom + self.world_height * self.scale

    @property
    def cell_step(self) -> float:
        """Screen size of one cell (logical pixels)."""
        return self.cell_size * self.scale

    # ------------------------------------------------------------------
    # Projection
    # ------------------------------------------------------------------
    def screen_to_world(self, sx: float, sy: float) -> Optional[Tuple[float, float]]:
        """Screen (logical) -> world position, or None if outside the world."""
        if self.scale <= 0:
            return None
        wx = (sx - self.left) / self.scale
        wy = (sy - self.bottom) / self.scale
        if 0.0 <= wx <= self.world_width and 0.0 <= wy <= self.world_height:
            return wx, wy
        return None

    def world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        """World -> screen (logical) position."""
        return (self.left + wx * self.scale, self.bottom + wy * self.scale)

    # ------------------------------------------------------------------
    # Cells (delegated grid math, consistent with IWorld)
    # ------------------------------------------------------------------
    def cell_index(self, x: float, y: float) -> Tuple[int, int]:
        """World position -> (column, row), clamped to the grid."""
        col = int(x // self.cell_size)
        row = int(y // self.cell_size)
        col = max(0, min(self.cols - 1, col))
        row = max(0, min(self.rows - 1, row))
        return col, row

    def cell_center(self, col: int, row: int) -> Tuple[float, float]:
        return (
            (col + 0.5) * self.cell_size,
            (row + 0.5) * self.cell_size,
        )

    def cell_bounds(self, col: int, row: int) -> Tuple[float, float, float, float]:
        """(left, bottom, width, height) of a cell in world units."""
        return (
            col * self.cell_size,
            row * self.cell_size,
            self.cell_size,
            self.cell_size,
        )

    def cell_screen_rect(self, col: int, row: int) -> Tuple[float, float, float, float]:
        """Integer-snapped screen (left, bottom, width, height) of a cell."""
        sx = self.left + col * self.cell_step
        sy = self.bottom + row * self.cell_step
        step = self.cell_step
        return (sx, sy, step, step)


def build_layout(viewport_w: float,
                 viewport_h: float,
                 world: IWorld,
                 sidebar_width: float = 0.0,
                 margin: float = 12.0) -> WorldLayout:
    """Compute the layout for a world inside a viewport.

    The world is drawn at a **1:1 preferred scale** (1 world unit = 1 screen
    pixel) when it fits; otherwise it is scaled down uniformly to fit the
    available area. Cell steps are integer-snapped so cell rectangles land on
    whole pixels, keeping the grid crisp and the hit-test exact.
    """
    cell_size = world.cell_size
    cols = world.cols
    rows = world.rows
    world_w = cols * cell_size
    world_h = rows * cell_size

    area_left = sidebar_width + 2.0 * margin
    area_bottom = margin
    area_w = max(1.0, viewport_w - area_left - margin)
    area_h = max(1.0, viewport_h - 2.0 * margin)

    # Scale to fit the available area. Cap at 1.0 only when the world is
    # smaller than the area and we want 1:1; otherwise let the world grow to
    # fill a maximised window so there is no grey border around it.
    scale = min(area_w / world_w, area_h / world_h)

    # Integer-snap the cell step so cells land on whole pixels.
    step = max(1.0, round(cell_size * scale))
    scale = step / cell_size

    drawn_w = world_w * scale
    drawn_h = world_h * scale
    left = area_left + (area_w - drawn_w) / 2.0
    bottom = area_bottom + (area_h - drawn_h) / 2.0
    # Snap the origin to whole pixels too.
    left = round(left)
    bottom = round(bottom)

    return WorldLayout(
        left=left,
        bottom=bottom,
        scale=scale,
        cell_size=cell_size,
        cols=cols,
        rows=rows,
        world_width=world_w,
        world_height=world_h,
    )
