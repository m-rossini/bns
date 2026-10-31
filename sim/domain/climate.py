"""Climate data shared by the environment strategies.

The season strategy owns the *amount of sun* the world gets. That is published
as a `SolarProfile`; the day/night strategy turns it into light and the weather
strategy combines it with the season's temperature, humidity and pressure to
decide which conditions are plausible.

`ClimateContext` is the immutable snapshot handed to the weather strategy on
every rebuild: it carries the season, the world geometry and the physical
baselines the weather needs, so a weather implementation never has to reach
back into the environment for scattered values.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Mapping

from sim.domain.visuals import SolarProfile, SeasonPalette


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _ramp(value: float, low: float, high: float) -> float:
    """0 below ``low``, 1 above ``high``, linear in between."""
    if high <= low:
        return 1.0 if value >= high else 0.0
    return clamp((value - low) / (high - low))


DEFAULT_WEATHER_WEIGHTS: Dict[str, float] = {
    "clear": 40.0,
    "cloudy": 30.0,
    "rain": 20.0,
    "storm": 10.0,
    "snow": 0.0,
}


@dataclass(frozen=True)
class ClimateContext:
    """Everything a weather strategy needs to describe the current climate.

    The fields are plain physical readings (deg C, 0..1 relative humidity,
    hPa) plus the world geometry, so implementations stay testable without a
    container or a renderer.
    """

    tick: int
    season: str
    season_progress: float
    solar: SolarProfile
    base_temperature: float
    temperature_swing: float
    humidity: float
    pressure_hpa: float
    #: Season weights, before the climate adjustments below.
    weather_weights: Mapping[str, float] = field(default_factory=dict)
    #: World geometry, in world units and cells.
    width: float = 1.0
    height: float = 1.0
    cols: int = 1
    rows: int = 1
    cell_size: float = 1.0

    @property
    def mean_temperature(self) -> float:
        """Seasonal mean temperature used for precipitation decisions."""
        return self.base_temperature

    @property
    def daylight_fraction(self) -> float:
        return self.solar.daylight_fraction

    @property
    def sun_intensity(self) -> float:
        return self.solar.sun_intensity

    def temperature_for_light(self, light: float) -> float:
        """Diurnal temperature from a 0..1 light reading."""
        return self.base_temperature + self.temperature_swing * (
            2.0 * clamp(light) - 1.0
        )

    def adjusted_weather_weights(self) -> Dict[str, float]:
        """Season weights reshaped by temperature, humidity and pressure.

        * rain is suppressed near/below freezing and in dry air;
        * leftover rain becomes snow when the season is cold enough;
        * snow melts away in warm seasons;
        * storms need warmth, moisture and low pressure;
        * clear skies dominate when the air is dry.
        """
        base = {
            str(kind): float(weight)
            for kind, weight in (self.weather_weights or DEFAULT_WEATHER_WEIGHTS).items()
            if float(weight) > 0.0
        }
        if not base:
            base = {"clear": 1.0}

        temperature = self.mean_temperature
        humidity = clamp(self.humidity)
        pressure = self.pressure_hpa

        adjusted: Dict[str, float] = {}
        for kind, weight in base.items():
            factor = 1.0
            if kind == "rain":
                factor *= _ramp(temperature, 1.0, 8.0)
                factor *= 0.55 + 0.9 * humidity
            elif kind == "snow":
                factor *= 1.0 - _ramp(temperature, 1.0, 6.0)
                factor *= 0.7 + 0.6 * humidity
            elif kind == "storm":
                factor *= 0.5 + 0.5 * _ramp(temperature, 6.0, 20.0)
                factor *= 0.5 + humidity
                factor *= 0.75 + 0.25 * (1.0 - _ramp(pressure, 995.0, 1015.0))
            elif kind == "clear":
                factor *= 1.2 - 0.5 * humidity
            elif kind == "cloudy":
                factor *= 0.9 + 0.4 * humidity
            adjusted[kind] = max(0.0, weight * factor)

        # Freezing rain falls as snow: move the (already climate-shaped) rain
        # weight instead of inventing snow in seasons that never allow it.
        if temperature <= 1.0 and adjusted.get("rain", 0.0) > 0.0:
            adjusted["snow"] = adjusted.get("snow", 0.0) + adjusted.pop("rain")

        if not any(value > 0.0 for value in adjusted.values()):
            adjusted = {"clear": 1.0}
        return adjusted

    def is_freezing(self) -> bool:
        return self.mean_temperature <= 1.0

    def humidity_band(self) -> str:
        if self.humidity < 0.35:
            return "dry"
        if self.humidity > 0.65:
            return "humid"
        return "temperate"

    def sun_angle_hint(self) -> float:
        """Peak solar altitude hint (0..1) derived from daylight length."""
        return math.sin(math.pi * clamp(self.daylight_fraction))

    @classmethod
    def from_palette(
        cls,
        *,
        tick: int,
        season: str,
        season_progress: float,
        palette: SeasonPalette,
        solar: SolarProfile,
        weather_weights: Mapping[str, float],
        world,
    ) -> "ClimateContext":
        """Build a context from a season palette plus the world geometry."""
        cols = getattr(world, "cols", 1) or 1
        rows = getattr(world, "rows", 1) or 1
        return cls(
            tick=tick,
            season=season,
            season_progress=clamp(season_progress),
            solar=solar,
            base_temperature=palette.base_temperature,
            temperature_swing=palette.temperature_swing,
            humidity=palette.humidity,
            pressure_hpa=palette.pressure_hpa,
            weather_weights=dict(weather_weights),
            width=float(getattr(world, "width", 1.0) or 1.0),
            height=float(getattr(world, "height", 1.0) or 1.0),
            cols=int(cols),
            rows=int(rows),
            cell_size=float(getattr(world, "cell_size", 1.0) or 1.0),
        )
