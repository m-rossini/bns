"""Colony Cluster placement strategy.

Seeds distinct bacterial colonies by grouping beans tightly around
randomized biological mother centroids whose count scales with world area.

All positions are **collision-free**: beans do not overlap each other, do not
overlap barriers, and stay inside the world bounds (accounting for bean
radius).

Tunable attributes:
* Area Per Cluster Metric
* Cluster Spread Standard Deviation (sigma)

Calculus:
    C = max(1, Round(A / AreaPerCluster))  total clusters
    Centroids chosen randomly within bounds.
    Beans per cluster distributed via 2D Gaussian (Box-Muller):
        dx = sigma * sqrt(-2 ln u1) * cos(2*pi u2)
        dy = sigma * sqrt(-2 ln u1) * sin(2*pi u2)
    where u1, u2 ~ Uniform(0, 1).
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

logger = get_logger("placement.colony_cluster")


class ColonyClusterStrategy(IPlacementStrategy):
    name = "colony_cluster"

    def __init__(
        self,
        area_per_cluster: float = 2000.0,
        cluster_spread_sigma: float = 30.0,
        seed: int = 1337,
    ):
        self.area_per_cluster = max(1.0, area_per_cluster)
        self.cluster_spread_sigma = cluster_spread_sigma
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
        c = max(1, round(area / self.area_per_cluster))

        # Centroids chosen randomly within bounds, margin to keep clusters visible.
        margin = min(width, height) * 0.05
        centroids: List[Position] = []
        for _ in range(c):
            cx = rng.uniform(margin, width - margin)
            cy = rng.uniform(margin, height - margin)
            centroids.append((cx, cy))

        beans_per_cluster = max(1, n // c)
        remainder = n % c

        points: List[Position] = list(existing or [])
        for cluster_idx, (cx, cy) in enumerate(centroids):
            count = beans_per_cluster + (1 if cluster_idx < remainder else 0)
            for _ in range(count):
                u1 = max(1e-9, rng.uniform(0.0, 1.0))
                u2 = rng.uniform(0.0, 1.0)
                factor = self.cluster_spread_sigma * math.sqrt(-2.0 * math.log(u1))
                dx = factor * math.cos(2.0 * math.pi * u2)
                dy = factor * math.sin(2.0 * math.pi * u2)
                x = cx + dx
                y = cy + dy
                # Clamp into bounds first, then collision-check.
                x = max(0.0, min(width, x))
                y = max(0.0, min(height, y))
                if not is_valid_bean_position(x, y, radius, world, points):
                    continue
                points.append((x, y))
                if len(points) - len(existing or []) >= n:
                    break
            if len(points) - len(existing or []) >= n:
                break

        new_points = points[len(existing or []):]
        logger.debug(
            "placement.colony_cluster requested=%d produced=%d clusters=%d",
            n,
            len(new_points),
            c,
        )
        return new_points[:n]
