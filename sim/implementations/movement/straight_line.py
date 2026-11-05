"""Straight-line movement strategy.

Every bean starts with the configured global direction and speed, then moves in
a straight line. When it reaches a world edge it reflects and continues; each
bean keeps its own velocity so it can bounce independently.

Collisions are detected after the move and logged, but do not change the
motion yet (bean-bean and bean-barrier events are separate).
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Sequence, Tuple

from sim.config import MovementConfig
from sim.domain.beans import Bean
from sim.interfaces.movement import IMovementStrategy
from sim.interfaces.world import IWorld
from sim.observability import get_logger, log_event
from sim.implementations.movement.numba_collisions import (
    check_barrier_collisions_numba,
    check_bean_collisions_numba,
    NUMBA_AVAILABLE,
)

logger = get_logger("movement.straight_line")


def _overlaps_barrier(bean_x: float, bean_y: float, radius: float, barrier) -> bool:
    if barrier.kind == "rect":
        left, bottom = barrier.x, barrier.y
        right, top = barrier.x + barrier.width, barrier.y + barrier.height
        cx = min(max(bean_x, left), right)
        cy = min(max(bean_y, bottom), top)
        dx, dy = bean_x - cx, bean_y - cy
        return dx * dx + dy * dy <= radius * radius
    if barrier.kind == "circle":
        cx = barrier.x + barrier.radius
        cy = barrier.y + barrier.radius
        dx, dy = bean_x - cx, bean_y - cy
        reach = radius + barrier.radius
        return dx * dx + dy * dy <= reach * reach
    return False


class StraightLineMovementStrategy(IMovementStrategy):
    name = "straight_line"

    def __init__(self, config: MovementConfig, bean_radius: float, world_width: float = 0.0, world_height: float = 0.0):
        self.config = config
        self.bean_radius = max(0.0, bean_radius)
        self.world_width = world_width
        self.world_height = world_height
        dx, dy = config.direction
        length = math.hypot(dx, dy)
        self.unit_direction: Tuple[float, float] = (dx / length, dy / length)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, beans: Sequence[Bean], world: IWorld, dt: float) -> None:
        if not beans or dt <= 0.0:
            return
        self._seed_velocities(beans)
        self._move(beans, world, dt)
        # Collision detection only feeds DEBUG logging for now (there is no
        # response), so skip the spatial work entirely unless DEBUG is on.
        if logger.isEnabledFor(logging.DEBUG):
            self._log_barrier_collisions(beans, world)
            self._log_bean_collisions(beans)

    def _seed_velocities(self, beans: Sequence[Bean]) -> None:
        """Give beans their initial velocity the first time they move."""
        speed = self.config.speed
        ux, uy = self.unit_direction
        for bean in beans:
            if bean.vx is None or bean.vy is None:
                bean.vx = ux * speed
                bean.vy = uy * speed

    def _move(self, beans: Sequence[Bean], world: IWorld, dt: float) -> None:
        radius = self.bean_radius
        min_x, max_x = radius, max(radius, world.width - radius)
        min_y, max_y = radius, max(radius, world.height - radius)
        bounce = self.config.bounce_on_edges
        log_bounces = logger.isEnabledFor(logging.DEBUG)

        for bean in beans:
            x = bean.x + bean.vx * dt
            y = bean.y + bean.vy * dt
            edges: List[str] = []

            if x < min_x:
                if bounce:
                    x = min_x + (min_x - x)
                    bean.vx = -bean.vx
                else:
                    x = min_x
                edges.append("left")
            elif x > max_x:
                if bounce:
                    x = max_x - (x - max_x)
                    bean.vx = -bean.vx
                else:
                    x = max_x
                edges.append("right")

            if y < min_y:
                if bounce:
                    y = min_y + (min_y - y)
                    bean.vy = -bean.vy
                else:
                    y = min_y
                edges.append("bottom")
            elif y > max_y:
                if bounce:
                    y = max_y - (y - max_y)
                    bean.vy = -bean.vy
                else:
                    y = max_y
                edges.append("top")

            # A large step could still leave the bean outside after reflection.
            if x < min_x:
                x = min_x
            elif x > max_x:
                x = max_x
            if y < min_y:
                y = min_y
            elif y > max_y:
                y = max_y

            bean.x = x
            bean.y = y

            if edges and log_bounces:
                log_event(
                    logger,
                    "bean.bounced",
                    level=logging.DEBUG,
                    bean_id=bean.id,
                    edge="+".join(edges),
                    x=round(bean.x, 3),
                    y=round(bean.y, 3),
                )

    # ------------------------------------------------------------------
    # Collision detection (logging only)
    # ------------------------------------------------------------------
    def _log_barrier_collisions(
        self, beans: Sequence[Bean], world: IWorld
    ) -> None:
        barriers = world.barriers
        if not barriers:
            return

        # Use numba-accelerated collision detection if available
        if NUMBA_AVAILABLE:
            collisions = check_barrier_collisions_numba(beans, barriers, self.bean_radius)
            for bean_idx, barrier_idx in collisions:
                bean = beans[bean_idx]
                barrier = barriers[barrier_idx]
                log_event(
                    logger,
                    "bean.collided_barrier",
                    level=logging.DEBUG,
                    bean_id=bean.id,
                    barrier_id=barrier.id,
                    x=round(bean.x, 3),
                    y=round(bean.y, 3),
                )
        else:
            # Fallback to pure Python
            radius = self.bean_radius
            for bean in beans:
                for barrier in barriers:
                    if _overlaps_barrier(bean.x, bean.y, radius, barrier):
                        log_event(
                            logger,
                            "bean.collided_barrier",
                            level=logging.DEBUG,
                            bean_id=bean.id,
                            barrier_id=barrier.id,
                            x=round(bean.x, 3),
                            y=round(bean.y, 3),
                        )

    def _log_bean_collisions(self, beans: Sequence[Bean]) -> None:
        if len(beans) < 2:
            return

        # Use numba-accelerated collision detection if available
        if NUMBA_AVAILABLE and self.world_width > 0 and self.world_height > 0:
            collisions = check_bean_collisions_numba(
                beans, self.bean_radius, self.world_width, self.world_height
            )
            for a_idx, b_idx in collisions:
                a = beans[a_idx]
                b = beans[b_idx]
                log_event(
                    logger,
                    "bean.collided_bean",
                    level=logging.DEBUG,
                    bean_id=a.id,
                    other_id=b.id,
                    x=round(a.x, 3),
                    y=round(a.y, 3),
                )
            return

        # Fallback to pure Python spatial hash
        cell = max(1.0, 2.0 * self.bean_radius)
        buckets: Dict[Tuple[int, int], List[Bean]] = {}
        for bean in beans:
            key = (int(bean.x // cell), int(bean.y // cell))
            buckets.setdefault(key, []).append(bean)

        reach_sq = (2.0 * self.bean_radius) ** 2
        for (cx, cy), bucket in buckets.items():
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    other = buckets.get((cx + dx, cy + dy))
                    if not other:
                        continue
                    for a in bucket:
                        for b in other:
                            if a.id >= b.id:
                                continue
                            ddx, ddy = a.x - b.x, a.y - b.y
                            if ddx * ddx + ddy * ddy < reach_sq:
                                log_event(
                                    logger,
                                    "bean.collided_bean",
                                    level=logging.DEBUG,
                                    bean_id=a.id,
                                    other_id=b.id,
                                    x=round(a.x, 3),
                                    y=round(a.y, 3),
                                )
