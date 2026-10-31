"""Poisson-Disc placement strategy.

Generates a semi-random, organic distribution with a strict minimum spacing
radius scaled dynamically to prevent cell overlap across any map size.

All positions are **collision-free**: beans do not overlap each other, do not
overlap barriers, and stay inside the world bounds (accounting for bean
radius).

Tunable attributes:
* Base Spacing Scale
* Maximum Retry Limit

Calculus:
    Minimum spacing radius r = sqrt(A / N) × BaseSpacingScale
    where A is total world area and N is the target population.

Candidate coordinates are sampled iteratively in an annulus (r to 2r)
surrounding existing valid points, validating spatial distance constraints
until N coordinates are established.
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

from sim.domain.beans import Bean, Position
from sim.domain.placement_utils import is_valid_bean_position
from sim.domain.world import World
from sim.interfaces.placement import IPlacementStrategy
from sim.observability import get_logger

logger = get_logger("placement.poisson_disc")


class PoissonDiscStrategy(IPlacementStrategy):
    name = "poisson_disc"

    def __init__(
        self,
        base_spacing_scale: float = 1.0,
        max_retry_limit: int = 100,
        seed: int = 1337,
    ):
        self.base_spacing_scale = base_spacing_scale
        self.max_retry_limit = max_retry_limit
        self.seed = seed

    def generate_positions(
        self,
        n: int,
        width: float,
        height: float,
        world: Optional[World] = None,
        existing: Optional[List[Bean]] = None,
        radius: float = 0.0,
    ) -> List[Position]:
        if n <= 0:
            return []
        if width <= 0 or height <= 0:
            return []

        rng = random.Random(self.seed)
        area = width * height
        # Minimum spacing radius scaled to density.
        spacing = math.sqrt(area / max(1, n)) * self.base_spacing_scale
        # Use the larger of the configured bean radius and the spacing radius.
        eff_radius = max(radius, spacing)
        radius_sq = eff_radius * eff_radius

        points: List[Position] = []
        # Grid-based spatial hash for fast neighbour queries.
        cell_size = max(1.0, eff_radius / math.sqrt(2.0))
        cols = max(1, int(math.ceil(width / cell_size)))
        rows = max(1, int(math.ceil(height / cell_size)))
        grid: List[List[Optional[int]]] = [[-1] * cols for _ in range(rows)]

        def _cell_index(px: float, py: float) -> Tuple[int, int]:
            return (
                min(cols - 1, max(0, int(px / cell_size))),
                min(rows - 1, max(0, int(py / cell_size))),
            )

        def _too_close(px: float, py: float) -> bool:
            gx, gy = _cell_index(px, py)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < cols and 0 <= ny < rows:
                        pi = grid[ny][nx]
                        if pi != -1:
                            qx, qy = points[pi]
                            if (px - qx) ** 2 + (py - qy) ** 2 < radius_sq:
                                return True
            return False

        attempts = 0
        max_attempts = self.max_retry_limit * max(1, n)
        while len(points) < n and attempts < max_attempts:
            attempts += 1
            px = rng.uniform(0, width)
            py = rng.uniform(0, height)
            if _too_close(px, py):
                continue
            # Collision-free check against barriers, borders and beans.
            if not is_valid_bean_position(px, py, eff_radius, world, existing):
                continue
            points.append((px, py))
            gx, gy = _cell_index(px, py)
            grid[gy][gx] = len(points) - 1

        logger.debug(
            "placement.poisson_disc requested=%d produced=%d spacing=%.3f attempts=%d",
            n,
            len(points),
            spacing,
            attempts,
        )
        return points
