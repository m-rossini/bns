"""Symmetrical Spawn Strategy.

Ensures rotational symmetry across world axes, providing competitive equity
or aesthetic balance in structured arenas.

All positions are **collision-free**: beans do not overlap each other, do not
overlap barriers, and stay inside the world bounds (accounting for bean
radius).

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
from typing import List, Optional, Tuple

from sim.domain.beans import Bean, Position
from sim.domain.placement_utils import is_valid_bean_position
from sim.domain.world import World
from sim.interfaces.placement import IPlacementStrategy
from sim.observability import get_logger

logger = get_logger("placement.symmetrical")


class SymmetricalStrategy(IPlacementStrategy):
    name = "symmetrical"

    def __init__(self, symmetry_axes: int = 4, seed: int = 1337):
        self.symmetry_axes = max(1, symmetry_axes)
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
        k = self.symmetry_axes
        cx, cy = width / 2.0, height / 2.0
        r_max = min(width, height) / 2.0
        n_per_segment = math.ceil(n / k)

        base_points: List[Position] = []
        for _ in range(n_per_segment):
            theta = rng.uniform(0.0, 2.0 * math.pi / k)
            r = r_max * math.sqrt(rng.uniform(0.0, 1.0))
            base_points.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))

        points: List[Position] = list(existing or [])
        seen: set = set((round(p.x, 3), round(p.y, 3)) for p in points)
        for base_x, base_y in base_points:
            for i in range(k):
                phi = i * 2.0 * math.pi / k
                x = cx + (base_x - cx) * math.cos(phi) - (base_y - cy) * math.sin(phi)
                y = cy + (base_x - cx) * math.sin(phi) + (base_y - cy) * math.cos(phi)
                # Clamp into bounds.
                x = max(0.0, min(width, x))
                y = max(0.0, min(height, y))
                key = (round(x, 3), round(y, 3))
                if key in seen:
                    continue
                # Collision-free check against barriers, borders and beans.
                if not is_valid_bean_position(x, y, radius, world, points):
                    continue
                seen.add(key)
                points.append((x, y))
                if len(points) - len(existing or []) >= n:
                    break
            if len(points) - len(existing or []) >= n:
                break

        new_points = points[len(existing or []):]
        logger.debug(
            "placement.symmetrical requested=%d produced=%d axes=%d",
            n,
            len(new_points),
            k,
        )
        return new_points
