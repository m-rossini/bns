"""Positional gradients.

A gradient maps a world position to a normalised factor in ``0..1`` along a
configured orientation, then interpolates a ``(start, end)`` pair. The same
primitive is used for:

* climate readings (temperature, humidity, pressure, light) in `Environment`
* the season ground colour over the course of a season

Orientations
------------
``north_south``  south edge (0) -> north edge (1)
``south_north``  north edge (0) -> south edge (1)
``west_east``    west edge (0)  -> east edge (1)
``east_west``    east edge (0)  -> west edge (1)
``centre_out``   world centre (0) -> edges/corners (1)
``out_centre``   edges/corners (1) -> world centre (0)
``diagonal_up``  south-west (0) -> north-east (1)
``diagonal_down`` north-west (0) -> south-east (1)

Unknown names fall back to ``north_south`` and log a warning, so a typo in
configuration never stops the simulation.
"""

import logging
import math
from dataclasses import dataclass
from typing import Tuple

from sim.config import GradientOrientation

logger = logging.getLogger("bean.gradient")

ORIENTATIONS: Tuple[GradientOrientation, ...] = tuple(GradientOrientation)

_DEFAULT_ORIENTATION = GradientOrientation.NORTH_SOUTH


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _normalise_orientation(orientation) -> GradientOrientation:
    """Normalise a string or enum value to a :class:`GradientOrientation`.

    Unknown names fall back to ``NORTH_SOUTH`` and log a warning, so a typo in
    configuration never stops the simulation.
    """
    if isinstance(orientation, GradientOrientation):
        return orientation
    if not orientation:
        return _DEFAULT_ORIENTATION
    key = str(orientation).strip().lower().replace("-", "_").replace(" ", "_")
    try:
        return GradientOrientation[key.upper()]
    except KeyError:
        logger.warning(
            "gradient.unknown_orientation orientation=%r fallback=%s",
            orientation,
            _DEFAULT_ORIENTATION.value,
        )
        return _DEFAULT_ORIENTATION


@dataclass(frozen=True)
class Gradient:
    """Interpolate a ``(start, end)`` pair across the world."""

    orientation: GradientOrientation = _DEFAULT_ORIENTATION
    start: float = 0.0
    end: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "orientation", _normalise_orientation(self.orientation)
        )

    # ------------------------------------------------------------------
    # Position
    # ------------------------------------------------------------------
    def factor(self, x: float, y: float, width: float, height: float) -> float:
        """Normalised position (0..1) for a point inside a width x height box."""
        if width <= 0 or height <= 0:
            return 0.0

        u = _clamp(x / width)
        v = _clamp(y / height)
        orientation = self.orientation

        if orientation == GradientOrientation.NORTH_SOUTH:
            value = v
        elif orientation == GradientOrientation.SOUTH_NORTH:
            value = 1.0 - v
        elif orientation == GradientOrientation.WEST_EAST:
            value = u
        elif orientation == GradientOrientation.EAST_WEST:
            value = 1.0 - u
        elif orientation == GradientOrientation.DIAGONAL_UP:
            value = (u + v) / 2.0
        elif orientation == GradientOrientation.DIAGONAL_DOWN:
            value = (u + (1.0 - v)) / 2.0
        else:  # CENTRE_OUT / OUT_CENTRE
            # Normalised radial distance from the centre; 1.0 at the furthest
            # corner of the box.
            dx = (u - 0.5) * 2.0
            dy = (v - 0.5) * 2.0
            radial = _clamp(math.hypot(dx, dy) / math.sqrt(2.0))
            value = (
                radial
                if orientation == GradientOrientation.CENTRE_OUT
                else 1.0 - radial
            )

        return _clamp(value)

    def value(self, x: float, y: float, width: float, height: float) -> float:
        """Interpolate ``start -> end`` at a world position."""
        t = self.factor(x, y, width, height)
        return self.start + (self.end - self.start) * t

    def signed(self, x: float, y: float, width: float, height: float) -> float:
        """A symmetric variant centred on zero.

        The pair is interpreted as ``(-magnitude, +magnitude)`` deltas around
        the world centre. Useful for readings that are added to a baseline.
        """
        magnitude = max(abs(self.start), abs(self.end))
        t = self.factor(x, y, width, height)
        return (t * 2.0 - 1.0) * magnitude
