"""Resource Gradient placement strategy.

Uses a 2D noise map scaled to world dimensions as a nutrient heatmap,
clustering initial beans around environmental hotspots.

All positions are **collision-free**: beans do not overlap each other, do not
overlap barriers, and stay inside the world bounds (accounting for bean
radius).

Calculus:
    Noise values v in [0, 1] sampled relative to map size.
    Dynamic spawn threshold T by density tier:
        Sparse T=0.75, Average T=0.50, Heavy T=0.25, Super T=0.05.
    Accept candidates where v >= T until population target N is met.
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

from sim.config import ResourceGradientConfig
from sim.domain.beans import Bean, Position
from sim.domain.placement_utils import is_valid_bean_position
from sim.domain.world import World
from sim.interfaces.placement import IPlacementStrategy
from sim.observability import get_logger

logger = get_logger("placement.resource_gradient")


class ResourceGradientStrategy(IPlacementStrategy):
    name = "resource_gradient"

    def __init__(self, config: ResourceGradientConfig, seed: int = 1337):
        self.config = config
        self.noise_frequency = max(1e-6, config.noise_frequency)
        self.threshold = max(0.0, min(1.0, config.threshold))
        self.seed = seed

    def _noise(self, x: float, y: float, rng: random.Random) -> float:
        """Deterministic pseudo-noise in [0, 1] from a seeded hash."""
        h = rng.random()
        v = math.sin(x * self.noise_frequency + h * 100.0) * math.cos(
            y * self.noise_frequency + h * 77.0
        )
        return (v + 1.0) / 2.0

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

        points: List[Position] = list(existing or [])
        attempts = 0
        max_attempts = n * 100
        while len(points) - len(existing or []) < n and attempts < max_attempts:
            attempts += 1
            x = rng.uniform(0.0, width)
            y = rng.uniform(0.0, height)
            if self._noise(x, y, rng) < self.threshold:
                continue
            if not is_valid_bean_position(x, y, radius, world, points):
                continue
            points.append((x, y))

        new_points = points[len(existing or []):]
        logger.debug(
            "placement.resource_gradient requested=%d produced=%d attempts=%d "
            "threshold=%.2f freq=%.4f",
            n,
            len(new_points),
            attempts,
            self.threshold,
            self.noise_frequency,
        )
        return new_points
