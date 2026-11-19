"""Straight-line movement strategy.

Every bean starts with a random direction (or configured global direction) and
speed, then moves in a straight line. When it reaches a world edge it reflects
and continues; each bean keeps its own velocity so it can bounce independently.

Collisions are detected after the move and logged, but do not change the
motion yet (bean-bean and bean-barrier events are separate).

Energy integration:
- Beans consume energy: metabolic_rate + drag_coefficient * speed² per tick
- Bouncing off edges costs extra energy (collision penalty)
- Beans with energy <= 0 become dormant (brown, no movement)
- Rest: each bean eases toward an environment-driven target speed — full
  cruise by day and in comfort, down toward ``rest_speed_fraction × speed``
  at night, in the cold, in the heat, and when hungry (at most
  ``genotype.acceleration`` per second). Dawn resilience is genetic: deep
  sleepers keep sleeping into brighter light; low energy deepens any rest
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Sequence, Tuple

from sim.config import MovementConfig
from sim.domain.beans import Bean
from sim.domain.genotype import apply_energy_cost
from sim.interfaces.movement import IMovementStrategy
from sim.interfaces.world import IWorld
from sim.observability import get_logger, log_event
from sim.implementations.movement.numba_collisions import (
    check_barrier_collisions_numba,
    check_bean_collisions_numba,
    NUMBA_AVAILABLE,
)
from sim.random import random_direction, get_rng

logger = get_logger("movement.straight_line")


# Activity thresholds: below the night mark beans fully rest, above the day
# mark they run at full activity, ramping linearly between. Dawn-resilient
# genotypes shift the day mark later (they keep sleeping into brighter light).
# Heat mirrors the cold ramp: above full comfort beans go sluggish again, so
# hot bright middays also slow the herd. Time of day, season and weather flow
# through automatically — light encodes the sun arc, weather and daylight
# fraction; temperature encodes season, weather and the climate gradient.
_NIGHT_LIGHT = 0.10      # light_at or below: full rest
_DAY_LIGHT = 0.60        # light_at or above: full activity (before resilience)
_RESILIENCE_DAY_SHIFT = 0.30  # how much later resilient beans wake up
_COLD_TEMP_C = 2.0       # temperature at or below: fully sluggish
_COMFORT_TEMP_C = 12.0   # temperature at or above: no cold slowdown
_COMFORT_MAX_C = 28.0    # temperature at or below: no heat slowdown
_HEAT_MAX_C = 38.0       # temperature at or above: fully sluggish from heat
# Floor of the energy scaling: hunger dims vigor, but even an empty bean keeps
# most of it, so the day/night rhythm stays visible instead of washing out.
_ENERGY_VIGOR_FLOOR = 0.60


# Energy cost for bouncing off world edges
BOUNCE_ENERGY_COST = 10.0


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
        # Global direction (used only when random_initial_direction=False)
        dx, dy = config.direction
        length = math.hypot(dx, dy)
        self.unit_direction: Tuple[float, float] = (dx / length, dy / length)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, beans: Sequence[Bean], world: IWorld, dt: float, environment=None) -> None:
        if not beans or dt <= 0.0:
            return
        self._seed_velocities(beans)
        self._move(beans, world, dt, environment)
        # Collision detection only feeds DEBUG logging for now (there is no
        # response), so skip the spatial work entirely unless DEBUG is on.
        if logger.isEnabledFor(logging.DEBUG):
            self._log_barrier_collisions(beans, world)
            self._log_bean_collisions(beans)

    def _seed_velocities(self, beans: Sequence[Bean]) -> None:
        """Give beans their initial velocity the first time they move."""
        speed = self.config.speed
        rng = get_rng()
        for bean in beans:
            if bean.vx is None or bean.vy is None:
                if self.config.random_initial_direction:
                    ux, uy = random_direction(rng)
                else:
                    ux, uy = self.unit_direction
                bean.vx = ux * speed
                bean.vy = uy * speed
                # Initialize phenotype velocity if available
                if bean.phenotype is not None:
                    bean.phenotype.velocity = (bean.vx, bean.vy)
                    bean.phenotype.current_speed = speed

    def _target_speed(self, bean: Bean, environment=None) -> float:
        """Cruise speed scaled by light, temperature, genes and energy.

        Vigor is the most limiting of the daylight ramp (shifted later by the
        bean's own dawn resilience, so deep sleepers keep sleeping past dawn),
        the cold ramp and the heat ramp. Low energy deepens sleep: vigor is
        scaled by the bean's remaining energy share, so hungry beans conserve
        instead of sprinting. Without an environment (unit tests) beans cruise.
        """
        cruise = self.config.speed
        if environment is None:
            return cruise
        light = environment.light_at(bean.x, bean.y)
        temp = environment.temperature_at(bean.x, bean.y)
        genotype = bean.genotype if bean.phenotype is not None else None
        resilience = 0.0
        if genotype is not None:
            resilience = max(0.0, min(1.0, genotype.dawn_resilience))
        day_light = _DAY_LIGHT + resilience * _RESILIENCE_DAY_SHIFT
        light_vigor = (light - _NIGHT_LIGHT) / (day_light - _NIGHT_LIGHT)
        cold_vigor = (temp - _COLD_TEMP_C) / (_COMFORT_TEMP_C - _COLD_TEMP_C)
        heat_vigor = (_HEAT_MAX_C - temp) / (_HEAT_MAX_C - _COMFORT_MAX_C)
        vigor = max(0.0, min(1.0, light_vigor, cold_vigor, heat_vigor))
        phenotype = bean.phenotype
        if phenotype is not None and genotype is not None and genotype.energy_capacity > 0:
            energy_share = max(
                0.0, min(1.0, phenotype.current_energy / genotype.energy_capacity)
            )
            vigor *= _ENERGY_VIGOR_FLOOR + (1.0 - _ENERGY_VIGOR_FLOOR) * energy_share
        floor = self.config.rest_speed_fraction
        return cruise * (floor + (1.0 - floor) * vigor)

    def _move(self, beans: Sequence[Bean], world: IWorld, dt: float, environment=None) -> None:
        radius = self.bean_radius
        min_x, max_x = radius, max(radius, world.width - radius)
        min_y, max_y = radius, max(radius, world.height - radius)
        bounce = self.config.bounce_on_edges
        log_bounces = logger.isEnabledFor(logging.DEBUG)

        for bean in beans:
            # Skip dormant beans
            if bean.phenotype is not None and bean.phenotype.is_dormant:
                continue

            # Current speed from velocity, eased toward the environmental
            # target (cruise by day, rest fraction at night or in the cold)
            # at most genotype.acceleration per second, so beans slow down
            # into rest and wake up gradually.
            speed = math.hypot(bean.vx, bean.vy) if bean.vx is not None and bean.vy is not None else 0.0
            target = self._target_speed(bean, environment)
            if target != speed:
                if bean.genotype is not None and dt > 0.0:
                    max_delta = bean.genotype.acceleration * dt
                else:
                    max_delta = math.inf
                if speed < target:
                    speed = min(target, speed + max_delta)
                else:
                    speed = max(target, speed - max_delta)
                magnitude = math.hypot(bean.vx or 0.0, bean.vy or 0.0)
                if magnitude > 1e-9:
                    scale = speed / magnitude
                    bean.vx = (bean.vx or 0.0) * scale
                    bean.vy = (bean.vy or 0.0) * scale
                elif target > 0.0:
                    bean.vx, bean.vy = (
                        self.unit_direction[0] * target,
                        self.unit_direction[1] * target,
                    )
                    speed = target

            x = bean.x + (bean.vx or 0.0) * dt
            y = bean.y + (bean.vy or 0.0) * dt
            edges: List[str] = []
            bounced = False

            # World edge collisions
            if x < min_x:
                if bounce:
                    x = min_x + (min_x - x)
                    bean.vx = -(bean.vx or 0.0)
                    bounced = True
                else:
                    x = min_x
                edges.append("left")
            elif x > max_x:
                if bounce:
                    x = max_x - (x - max_x)
                    bean.vx = -(bean.vx or 0.0)
                    bounced = True
                else:
                    x = max_x
                edges.append("right")

            if y < min_y:
                if bounce:
                    y = min_y + (min_y - y)
                    bean.vy = -(bean.vy or 0.0)
                    bounced = True
                else:
                    y = min_y
                edges.append("bottom")
            elif y > max_y:
                if bounce:
                    y = max_y - (y - max_y)
                    bean.vy = -(bean.vy or 0.0)
                    bounced = True
                else:
                    y = max_y
                edges.append("top")

            # Barrier collisions - resolve by reflecting and pushing out
            barrier_bounced = self._resolve_barrier_collisions(bean, world, radius, x, y)
            bounced = bounced or barrier_bounced

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

            # Apply energy costs if bean has genotype/phenotype
            if bean.genotype is not None and bean.phenotype is not None:
                # Calculate acceleration (change in speed)
                old_speed = bean.phenotype.current_speed
                new_speed = math.hypot(bean.vx or 0.0, bean.vy or 0.0)
                acceleration = (new_speed - old_speed) / dt if dt > 0 else 0.0

                # Apply metabolic + drag + acceleration cost
                apply_energy_cost(
                    bean.phenotype,
                    bean.genotype,
                    dt,
                    speed=new_speed,
                    acceleration=acceleration,
                )

                # Extra cost for bouncing (world edges or barriers)
                if bounced:
                    bean.phenotype.current_energy = max(
                        0.0, bean.phenotype.current_energy - BOUNCE_ENERGY_COST
                    )
                    if bean.phenotype.current_energy <= 0.0:
                        bean.phenotype.is_dormant = True
                        bean.phenotype.current_speed = 0.0
                        bean.phenotype.velocity = (0.0, 0.0)
                        bean.vx = 0.0
                        bean.vy = 0.0

                # Update phenotype (aging runs centrally in the tick loop)
                bean.phenotype.current_speed = new_speed
                bean.phenotype.velocity = (bean.vx or 0.0, bean.vy or 0.0)
                bean.phenotype.update_color(bean.genotype)
                bean.update_color_from_phenotype()

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

    def _resolve_barrier_collisions(
        self, bean: Bean, world: IWorld, radius: float, x: float, y: float
    ) -> bool:
        """Resolve bean-barrier collisions by reflecting velocity and pushing out.

        Returns True if any collision occurred.
        """
        barriers = world.barriers
        if not barriers:
            return False

        bounced = False
        for barrier in barriers:
            if not _overlaps_barrier(x, y, radius, barrier):
                continue

            # Compute collision normal (direction from barrier center to bean)
            if barrier.kind == "rect":
                # Find closest point on rectangle to bean center
                left, bottom = barrier.x, barrier.y
                right, top = barrier.x + barrier.width, barrier.y + barrier.height
                cx = min(max(x, left), right)
                cy = min(max(y, bottom), top)
                nx, ny = x - cx, y - cy
            elif barrier.kind == "circle":
                cx = barrier.x + barrier.radius
                cy = barrier.y + barrier.radius
                nx, ny = x - cx, y - cy
            else:
                continue

            # Normalize
            dist = math.hypot(nx, ny)
            if dist == 0.0:
                # Bean center exactly at barrier center - push in random direction
                nx, ny = 1.0, 0.0
                dist = 1.0
            else:
                nx, ny = nx / dist, ny / dist

            # Reflect velocity around normal
            # v' = v - 2(v·n)n
            vx = bean.vx or 0.0
            vy = bean.vy or 0.0
            dot = vx * nx + vy * ny
            bean.vx = vx - 2 * dot * nx
            bean.vy = vy - 2 * dot * ny

            # Push bean out of barrier
            overlap = radius - dist
            if overlap > 0:
                x += nx * overlap * 1.01  # Slight extra to avoid sticking
                y += ny * overlap * 1.01

            bounced = True

        return bounced

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
