"""Border-to-Center Radial placement strategy (Periphery-Heavy).

Spawns cells in an outer ring / donut configuration along the perimeter,
keeping the central area clear.

Tunable attributes:
* Outer Ring Thickness Ratio

Calculus:
    R_min = R_max * (1 - RingThicknessRatio)
    r = sqrt(R_min^2 + u * (R_max^2 - R_min^2)), u ~ Uniform(0, 1)
    theta ~ Uniform(0, 2pi)
    x = Center.x + r * cos(theta), y = Center.y + r * sin(theta)
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple

from sim.domain.beans import Position
from sim.interfaces.placement import IPlacementStrategy
from sim.observability import get_logger

logger = get_logger("placement.border_to_center")


class BorderToCenterStrategy(IPlacementStrategy):
    name = "border_to_center"

    def __init__(
        self, ring_thickness_ratio: float = 0.3, seed: int = 1337
    ):
        self.ring_thickness_ratio = max(0.0, min(1.0, ring_thickness_ratio))
        self.seed = seed

    def generate_positions(
        self, n: int, width: float, height: float
    ) -> List[Position]:
        if n <= 0:
            return []
        if width <= 0 or height <= 0:
            return []

        rng = random.Random(self.seed)
        cx, cy = width / 2.0, height / 2.0
        r_max = min(width, height) / 2.0
        ratio = self.ring_thickness_ratio
        r_min = r_max * (1.0 - ratio)

        points: List[Position] = []
        for _ in range(n):
            u = rng.uniform(0.0, 1.0)
            r = math.sqrt(r_min * r_min + u * (r_max * r_max - r_min * r_min))
            theta = rng.uniform(0.0, 2.0 * math.pi)
            x = max(0.0, min(width, cx + r * math.cos(theta)))
            y = max(0.0, min(height, cy + r * math.sin(theta)))
            points.append((x, y))

        logger.debug(
            "placement.border_to_center requested=%d produced=%d ratio=%.2f",
            n,
            len(points),
            ratio,
        )
        return points
