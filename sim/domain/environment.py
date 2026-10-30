"""Concrete Environment implementation.

Aggregates the tick clock and optional strategy instances. Also derives
presentation-ready values (season, phase, light, weather) and a simple
temperature field that combines season, time of day, weather, and a smooth
microclimate variation across the world.
"""

import math
from typing import Optional

from sim.interfaces.environment import (
    IDayNightStrategy,
    IEnvironment,
    ISeasonStrategy,
    IWeatherStrategy,
)

_SEASON_BASE_C = {"spring": 14.0, "summer": 25.0, "autumn": 13.0, "winter": 3.0}
_SEASON_SWING_C = {"spring": 7.0, "summer": 6.0, "autumn": 7.0, "winter": 5.0}
_WEATHER_OFFSET_C = {
    "clear": 2.0,
    "cloudy": 0.0,
    "rain": -2.0,
    "storm": -4.0,
    "snow": -5.0,
}


class Environment(IEnvironment):
    def __init__(
        self,
        weather_strategy: Optional[IWeatherStrategy] = None,
        season_strategy: Optional[ISeasonStrategy] = None,
        daynight_strategy: Optional[IDayNightStrategy] = None,
    ):
        self._tick = 0
        self._weather_strategy = weather_strategy
        self._season_strategy = season_strategy
        self._daynight_strategy = daynight_strategy

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def weather_strategy(self) -> Optional[IWeatherStrategy]:
        return self._weather_strategy

    @property
    def season_strategy(self) -> Optional[ISeasonStrategy]:
        return self._season_strategy

    @property
    def daynight_strategy(self) -> Optional[IDayNightStrategy]:
        return self._daynight_strategy

    @property
    def weather(self) -> str:
        if self._weather_strategy is None:
            return "clear"
        return self._weather_strategy.weather

    @property
    def season(self) -> str:
        if self._season_strategy is None:
            return "spring"
        return self._season_strategy.get_season(self._tick)

    @property
    def phase(self) -> str:
        if self._daynight_strategy is None:
            return "day"
        return self._daynight_strategy.get_phase(self._tick)

    @property
    def light_level(self) -> float:
        if self._daynight_strategy is None:
            return 0.7
        return self._daynight_strategy.get_light_level(self._tick)

    def temperature_at(self, x: float, y: float) -> float:
        """Temperature in Celsius for a world position.

        Seasonal mean + diurnal swing (driven by light) + weather offset +
        a smooth microclimate pattern so different spots read differently.
        """
        season = self.season
        base = _SEASON_BASE_C.get(season, 14.0)
        swing = _SEASON_SWING_C.get(season, 7.0)
        temperature = base + swing * (2.0 * self.light_level - 1.0)
        temperature += _WEATHER_OFFSET_C.get(self.weather, 0.0)

        # Smooth position-dependent variation (about +/- 3 C).
        microclimate = 2.2 * math.sin(x / 210.0) * math.cos(y / 170.0)
        microclimate += 0.8 * math.sin((x + y) / 95.0)
        temperature += microclimate

        return round(temperature, 1)

    def advance_tick(self) -> None:
        self._tick += 1
        if self._weather_strategy is not None:
            self._weather_strategy.update(self._tick, self)

    def reset(self) -> None:
        self._tick = 0
        if self._weather_strategy is not None:
            self._weather_strategy.reset()
