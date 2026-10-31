"""Barrier strategy: configurable colour, span limits and placement.

Barriers are axis-aligned rectangles snapped to the cell grid. Each one spans
at most ``BarrierConfig.max_span_cells`` cells in either direction, so 3x3,
3x1, 1x2 and 2x2 are valid while 4x1 is rejected. The fill colour is part of
the strategy, so every barrier reads the same unless a different strategy is
wired in.

Placement is deterministic: the same seed always yields the same barriers,
which keeps runs reproducible and the screenshots stable.
"""

import math
import random
from typing import List, Tuple

from sim.components import Barrier
from sim.config import BarrierConfig
from sim.interfaces.barrier import IBarrierStrategy
from sim.interfaces.world import IWorld
from sim.observability import get_logger

logger = get_logger("barrier")

_EPSILON = 1e-6


class BarrierStrategy(IBarrierStrategy):
    def __init__(self, config: BarrierConfig):
        self._config = config

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------
    @property
    def color(self) -> Tuple[int, int, int]:
        return tuple(self._config.color)

    @property
    def max_span_cells(self) -> int:
        return self._config.max_span_cells

    def span_cells(self, barrier: Barrier, world: IWorld) -> Tuple[int, int]:
        """Cells covered per axis; a circle uses its diameter."""
        cell = max(_EPSILON, world.cell_size)
        if barrier.kind == "circle":
            diameter = 2.0 * max(0.0, barrier.radius)
            span = max(1, int(math.ceil(diameter / cell - _EPSILON)))
            return span, span
        cols = max(1, int(math.ceil(max(0.0, barrier.width) / cell - _EPSILON)))
        rows = max(1, int(math.ceil(max(0.0, barrier.height) / cell - _EPSILON)))
        return cols, rows

    def validate(self, barrier: Barrier, world: IWorld) -> None:
        if barrier.kind not in ("rect", "circle"):
            raise ValueError(
                f"Barrier {barrier.id} has unknown kind {barrier.kind!r}"
            )
        if barrier.kind == "rect":
            if barrier.width <= 0 or barrier.height <= 0:
                raise ValueError(
                    f"Barrier {barrier.id} must have positive width and height"
                )
        elif barrier.radius <= 0:
            raise ValueError(f"Barrier {barrier.id} must have a positive radius")

        limit = self._config.max_span_cells
        cols, rows = self.span_cells(barrier, world)
        if cols > limit or rows > limit:
            raise ValueError(
                f"Barrier {barrier.id} spans {cols}x{rows} cells; "
                f"the limit is {limit}x{limit}"
            )

        left, bottom = barrier.x, barrier.y
        right = left + (2 * barrier.radius if barrier.kind == "circle" else barrier.width)
        top = bottom + (2 * barrier.radius if barrier.kind == "circle" else barrier.height)
        if left < -_EPSILON or bottom < -_EPSILON:
            raise ValueError(f"Barrier {barrier.id} starts outside the world")
        if right > world.width + _EPSILON or top > world.height + _EPSILON:
            raise ValueError(f"Barrier {barrier.id} ends outside the world")

    # ------------------------------------------------------------------
    # Placement
    # ------------------------------------------------------------------
    def create_barriers(self, world: IWorld) -> List[Barrier]:
        config = self._config
        rng = random.Random(config.seed)
        cell = world.cell_size
        cols, rows = world.cols, world.rows
        margin = min(config.margin_cells, max(0, min(cols, rows) // 4))

        barriers: List[Barrier] = []
        placed: List[Tuple[int, int, int, int]] = []
        for index in range(config.count):
            span_cols = rng.randint(
                min(config.min_span_cells, config.max_span_cells),
                config.max_span_cells,
            )
            span_rows = rng.randint(
                min(config.min_span_cells, config.max_span_cells),
                config.max_span_cells,
            )
            span_cols = min(span_cols, max(1, cols - 2 * margin))
            span_rows = min(span_rows, max(1, rows - 2 * margin))

            max_col = max(margin, cols - margin - span_cols)
            max_row = max(margin, rows - margin - span_rows)
            col = rng.randint(min(margin, max_col), max_col)
            row = rng.randint(min(margin, max_row), max_row)

            # Try a few deterministic reshuffles before accepting an overlap.
            for _ in range(24):
                if not _overlaps(placed, col, row, span_cols, span_rows):
                    break
                col = rng.randint(min(margin, max_col), max_col)
                row = rng.randint(min(margin, max_row), max_row)

            placed.append((col, row, span_cols, span_rows))
            barrier = Barrier(
                id=index + 1,
                kind="rect",
                x=col * cell,
                y=row * cell,
                width=span_cols * cell,
                height=span_rows * cell,
                color=self.color,
            )
            self.validate(barrier, world)
            barriers.append(barrier)

        logger.info(
            "barrier.generated count=%s max_span_cells=%s color=%s",
            len(barriers),
            config.max_span_cells,
            self.color,
        )
        for barrier in barriers:
            cols_span, rows_span = self.span_cells(barrier, world)
            logger.debug(
                "barrier.rect id=%s x=%.1f y=%.1f span=%sx%s cells",
                barrier.id,
                barrier.x,
                barrier.y,
                cols_span,
                rows_span,
            )
        return barriers


def _overlaps(
    placed: List[Tuple[int, int, int, int]],
    col: int,
    row: int,
    span_cols: int,
    span_rows: int,
) -> bool:
    for other_col, other_row, other_cols, other_rows in placed:
        if (
            col < other_col + other_cols
            and other_col < col + span_cols
            and row < other_row + other_rows
            and other_row < row + span_rows
        ):
            return True
    return False
