"""Border-to-Center Radial placement strategy (Periphery-Heavy).

Spawns cells in an outer ring / donut configuration along the perimeter,
keeping the central area clear.

All positions are **collision-free**: beans do not overlap each other, do not
overlap barriers, and stay inside the world bounds (accounting for bean
radius).

Calculus:
    R_min = R_max * (1 - RingThicknessRatio)
    r = sqrt(R_min^2 + u * (R_max^2 - R_min^2)), u ~ Uniform(0, 1)
    theta ~ Uniform(0, 2pi)
    x = Center.x + r * cos(theta), y = Center.y + r * sin(theta)
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

from sim.config import BorderToCenterConfig
from sim.domain.beans import Bean, Position
from sim.domain.placement_utils import is_valid_bean_position
from sim.domain.world import World
from sim.interfaces.placement import IPlacementStrategy
from sim.observability import get_logger

logger = get_logger("placement.border_to_center")


class BorderToCenterStrategy(IPlacementStrategy):
    name = "border_to_center"

    def __init__(self, config: BorderToCenterConfig, seed: int = 1337):
        self.config = config
        self.ring_thickness_ratio = max(0.0, min(1.0, config.ring_thickness_ratio))
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
        cx, cy = width / 2.0, height / 2.0
        r_max = min(width, height) / 2.0
        ratio = self.ring_thickness_ratio
        r_min = r_max * (1.0 - ratio)

        points: List[Position] = list(existing or [])
        for _ in range(n):
            u = rng.uniform(0.0, 1.0)
            r = math.sqrt(r_min * r_min + u * (r_max * r_max - r_min * r_min))
            theta = rng.uniform(0.0, 2.0 * math.pi)
            x = max(0.0, min(width, cx + r * math.cos(theta)))
            y = max(0.0, min(height, cy + r * math.sin(theta)))
            if not is_valid_bean_position(x, y, radius, world, points):
                continue
            points.append((x, y))
            if len(points) - len(existing or []) >= n:
                break

        new_points = points[len(existing or []):]
        logger.debug(
            "placement.border_to_center requested=%d produced=%d ratio=%.2f",
            n,
            len(new_points),
            ratio,
        )
        return new_points
