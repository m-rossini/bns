"""Plain presentation data produced by the environment strategies.

No behaviour: the renderer only consumes these values, so all colours and
positions come from the strategies (and their config) instead of the view.
"""

from dataclasses import dataclass
from typing import Tuple

Color = Tuple[int, int, int]


@dataclass(frozen=True)
class SolarProfile:
    """How much sun the current season delivers.

    Owned by the season strategy; the day/night strategy derives the light
    curve from it and the weather strategy derives its climate baselines.

    ``sun_intensity`` is the peak brightness (1.0 = neutral, >1 = brighter
    summer sun), ``daylight_fraction`` is the share of the day the sun is
    above the horizon (0.5 = twelve hours).
    """

    sun_intensity: float = 1.0
    daylight_fraction: float = 0.5


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
    #: Peak sun brightness the season allows (>1 summer, <1 winter).
    sun_intensity: float = 1.0
    #: Share of the day with the sun above the horizon (0.5 = 12 h).
    daylight_fraction: float = 0.5
    #: Human-readable meaning of this season's ground colour (from the
    #  season strategy's config). Shown in the view legend.
    ground_meaning: str = "growing season"


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
