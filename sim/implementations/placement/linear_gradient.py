"""Linear Gradient placement strategy.

Applies a directional density bias, scaling cell concentration across world
boundaries from one side of the map to the other.

Tunable attributes:
* Directional Vector Angle
* Bias Curve Strength

Calculus:
    Project candidate onto directional vector -> normalized t in [0, 1].
    Acceptance-rejection sampling with linear weight:
        P(t) = 1 + BiasStrength * (t - 0.5)
    Reject candidates where random() > P(t) / max_weight.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple

from sim.domain.beans import Position
from sim.interfaces.placement import IPlacementStrategy
from sim.observability import get_logger

logger = get_logger("placement.linear_gradient")


class LinearGradientStrategy(IPlacementStrategy):
    name = "linear_gradient"

    def __init__(
        self,
        direction_angle: float = 0.0,
        bias_strength: float = 1.5,
        seed: int = 1337,
    ):
        self.direction_angle = direction_angle
        self.bias_strength = bias_strength
        self.seed = seed

    def generate_positions(
        self, n: int, width: float, height: float
    ) -> List[Position]:
        if n <= 0:
            return []
        if width <= 0 or height <= 0:
            return []

        rng = random.Random(self.seed)
        vx = math.cos(self.direction_angle)
        vy = math.sin(self.direction_angle)
        cx, cy = width / 2.0, height / 2.0

        # Max projection distance from center along the direction.
        max_proj = max(width, height) / 2.0
        max_weight = 1.0 + abs(self.bias_strength) * 0.5

        points: List[Position] = []
        attempts = 0
        max_attempts = n * 50
        while len(points) < n and attempts < max_attempts:
            attempts += 1
            x = rng.uniform(0.0, width)
            y = rng.uniform(0.0, height)
            # Normalized projection t in [0, 1] along direction.
            t = ((x - cx) * vx + (y - cy) * vy) / max_proj + 0.5
            t = max(0.0, min(1.0, t))
            weight = 1.0 + self.bias_strength * (t - 0.5)
            if rng.uniform(0.0, max_weight) <= weight:
                points.append((x, y))

        logger.debug(
            "placement.linear_gradient requested=%d produced=%d attempts=%d "
            "angle=%.2f bias=%.2f",
            n,
            len(points),
            attempts,
            self.direction_angle,
            self.bias_strength,
        )
        return points
