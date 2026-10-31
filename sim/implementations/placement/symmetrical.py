"""Symmetrical Spawn Strategy.

Ensures rotational symmetry across world axes, providing competitive equity
or aesthetic balance in structured arenas.

Tunable attributes:
* Symmetry Axes Count (k >= 1)

Calculus:
    N_w = ceil(N / k)  target count per symmetrical segment
    Base coordinates generated randomly within a primary slice
    (theta in [0, 2*pi/k]), radius r = R_max * sqrt(u).
    Replicated across k rotational axes via rotation transform.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple

from sim.domain.beans import Position
from sim.interfaces.placement import IPlacementStrategy
from sim.observability import get_logger

logger = get_logger("placement.symmetrical")


class SymmetricalStrategy(IPlacementStrategy):
    name = "symmetrical"

    def __init__(self, symmetry_axes: int = 4, seed: int = 1337):
        self.symmetry_axes = max(1, symmetry_axes)
        self.seed = seed

    def generate_positions(
        self, n: int, width: float, height: float
    ) -> List[Position]:
        if n <= 0:
            return []
        if width <= 0 or height <= 0:
            return []

        rng = random.Random(self.seed)
        k = self.symmetry_axes
        cx, cy = width / 2.0, height / 2.0
        r_max = min(width, height) / 2.0
        n_per_segment = math.ceil(n / k)

        base_points: List[Position] = []
        for _ in range(n_per_segment):
            theta = rng.uniform(0.0, 2.0 * math.pi / k)
            r = r_max * math.sqrt(rng.uniform(0.0, 1.0))
            base_points.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))

        points: List[Position] = []
        seen: set = set()
        for base_x, base_y in base_points:
            for i in range(k):
                phi = i * 2.0 * math.pi / k
                x = cx + (base_x - cx) * math.cos(phi) - (base_y - cy) * math.sin(phi)
                y = cy + (base_x - cx) * math.sin(phi) + (base_y - cy) * math.cos(phi)
                # Clamp into bounds.
                x = max(0.0, min(width, x))
                y = max(0.0, min(height, y))
                key = (round(x, 3), round(y, 3))
                if key not in seen:
                    seen.add(key)
                    points.append((x, y))
                if len(points) >= n:
                    break
            if len(points) >= n:
                break

        points = points[:n]
        logger.debug(
            "placement.symmetrical requested=%d produced=%d axes=%d",
            n,
            len(points),
            k,
        )
        return points
