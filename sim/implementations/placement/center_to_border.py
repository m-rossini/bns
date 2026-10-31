"""Center-to-Border Radial placement strategy (Core-Heavy).

Biases spawn probability toward the exact center of the map, creating a dense
central nucleus that thins exponentially toward the perimeter.

Tunable attributes:
* Falloff Exponent Curve

Calculus:
    r = R_max * u^FalloffExponent,  u ~ Uniform(0, 1)
    theta ~ Uniform(0, 2pi)
    x = Center.x + r * cos(theta), y = Center.y + r * sin(theta)

A higher falloff exponent concentrates more beans near the center.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple

from sim.domain.beans import Position
from sim.interfaces.placement import IPlacementStrategy
from sim.observability import get_logger

logger = get_logger("placement.center_to_border")


class CenterToBorderStrategy(IPlacementStrategy):
    name = "center_to_border"

    def __init__(self, falloff_exponent: float = 2.0, seed: int = 1337):
        self.falloff_exponent = max(0.1, falloff_exponent)
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
        exp = self.falloff_exponent

        points: List[Position] = []
        for _ in range(n):
            u = rng.uniform(0.0, 1.0)
            r = r_max * (u ** exp)
            theta = rng.uniform(0.0, 2.0 * math.pi)
            x = max(0.0, min(width, cx + r * math.cos(theta)))
            y = max(0.0, min(height, cy + r * math.sin(theta)))
            points.append((x, y))

        logger.debug(
            "placement.center_to_border requested=%d produced=%d exponent=%.2f",
            n,
            len(points),
            exp,
        )
        return points
