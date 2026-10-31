"""Plain presentation data produced by the environment strategies.

No behaviour: the renderer only consumes these values, so all colours and
positions come from the strategies (and their config) instead of the view.
"""

from dataclasses import dataclass, field
from typing import Tuple

Color = Tuple[int, int, int]


@dataclass(frozen=True)
class SeasonPalette:
    """Appearance and physical parameters for the current season."""

    name: str
    ground: Color
    details: Tuple[Color, ...]
    base_temperature: float
    temperature_swing: float
    humidity: float
    pressure_hpa: float


@dataclass(frozen=True)
class SkyPalette:
    night: Color
    day: Color
    twilight: Color
    overcast: Color
    sun: Color
    moon: Color
    star: Color


@dataclass(frozen=True)
class CelestialState:
    """Normalised positions (0..1) of the sun and moon along their arc."""

    sun_progress: float
    moon_progress: float
    sun_visible: bool
    moon_visible: bool
    moon_illumination: float


@dataclass(frozen=True)
class WeatherAppearance:
    """Per-condition tint and fallback text colour."""

    tint: Color
    label: Color
    opacity: float = 0.0
