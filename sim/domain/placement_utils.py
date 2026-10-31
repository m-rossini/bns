"""Collision-free placement utilities.

All placement strategies share these helpers so that every bean is guaranteed
to be:

* inside the world bounds (accounting for the bean radius),
* not overlapping any barrier,
* not overlapping any previously placed bean.

Strategies should call :func:`is_valid_bean_position` before accepting a
candidate coordinate, and retry until a valid one is found (or the retry
limit is exhausted).
"""

from __future__ import annotations

from typing import List, Tuple

from sim.domain.beans import Bean
from sim.domain.world import World

#: A world position (x, y).
Position = Tuple[float, float]


def _closest_point_in_rect(px: float, py: float, barrier) -> Tuple[float, float]:
    """Closest point on a rectangular barrier to (px, py)."""
    left = barrier.x
    bottom = barrier.y
    right = barrier.x + barrier.width
    top = barrier.y + barrier.height
    cx = min(max(px, left), right)
    cy = min(max(py, bottom), top)
    return (cx, cy)


def bean_collides_with_barrier(
    x: float, y: float, radius: float, world: World
) -> bool:
    """Return True if a bean of ``radius`` at ``(x, y)`` overlaps any barrier."""
    radius_sq = radius * radius
    for barrier in world.barriers:
        if barrier.kind != "rect":
            continue
        cx, cy = _closest_point_in_rect(x, y, barrier)
        dx = x - cx
        dy = y - cy
        if dx * dx + dy * dy <= radius_sq:
            return True
    return False


def bean_collides_with_beans(
    x: float, y: float, radius: float, existing: List[Tuple[float, float]]
) -> bool:
    """Return True if a bean of ``radius`` at ``(x, y)`` overlaps an existing bean.

    ``existing`` entries may be :class:`sim.domain.beans.Bean` objects or plain
    ``(x, y)`` position tuples.
    """
    radius_sq = (2.0 * radius) ** 2  # two beans of the same radius
    if existing is None:
        return False
    for bean in existing:
        bx = bean.x if hasattr(bean, "x") else bean[0]
        by = bean.y if hasattr(bean, "y") else bean[1]
        dx = x - bx
        dy = y - by
        if dx * dx + dy * dy <= radius_sq:
            return True
    return False


def is_valid_bean_position(
    x: float,
    y: float,
    radius: float,
    world: World,
    existing: List[Tuple[float, float]],
) -> bool:
    """Return True if a bean of ``radius`` at ``(x, y)`` is placement-valid.

    A position is valid when:

    * the whole bean fits inside the world bounds (margin = radius),
    * it does not overlap any barrier,
    * it does not overlap any already-placed bean.
    """
    # Must fit inside the world with the bean fully contained.
    if x < radius or x > world.width - radius:
        return False
    if y < radius or y > world.height - radius:
        return False
    if bean_collides_with_barrier(x, y, radius, world):
        return False
    if bean_collides_with_beans(x, y, radius, existing):
        return False
    return True


def clamp_to_bounds(x: float, y: float, world: World) -> Position:
    """Clamp a position into the world bounds (no radius margin)."""
    cx = min(max(x, 0.0), world.width)
    cy = min(max(y, 0.0), world.height)
    return (cx, cy)
