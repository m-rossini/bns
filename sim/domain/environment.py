"""Concrete Environment implementation.

Composes the calendar and the three optional strategies. Every environmental
reading is a function of position:

* ``weather_at(x, y)``     — per-cell weather field
* ``light_at(x, y)``       — sun altitude * local shading * weather dimming
* ``humidity_at(x, y)``    — seasonal baseline + weather + local variation
* ``pressure_at(x, y)``    — seasonal baseline + weather + local variation
* ``temperature_at(x, y)`` — seasonal mean + diurnal light + weather + microclimate

With a strategy set to ``None`` the environment still runs, and that reading
falls back to a documented constant ("static" mode).
"""

import math
from typing import Optional

from sim.domain.calendar import Calendar
from sim.domain.visuals import SeasonPalette
from sim.interfaces.environment import (
    ICalendar,
    IDayNightStrategy,
    IEnvironment,
    ISeasonStrategy,
    IWeatherStrategy,
)
from sim.interfaces.world import IWorld

_WEATHER_TEMP_C = {"clear": 2.0, "cloudy": 0.0, "rain": -2.0, "storm": -4.0, "snow": -5.0}
_WEATHER_HUMIDITY = {
    "clear": -0.10, "cloudy": 0.02, "rain": 0.20, "storm": 0.25, "snow": 0.08,
}
_WEATHER_PRESSURE_HPA = {
    "clear": 4.0, "cloudy": -3.0, "rain": -8.0, "storm": -18.0, "snow": -5.0,
}
_WEATHER_LIGHT = {"clear": 1.0, "cloudy": 0.82, "rain": 0.68, "storm": 0.5, "snow": 0.85}

_STATIC_LIGHT = 0.7
_STATIC_PALETTE = SeasonPalette(
    name="Static",
    ground=(110, 150, 110),
    details=((140, 170, 140),),
    base_temperature=14.0,
    temperature_swing=7.0,
    humidity=0.5,
    pressure_hpa=1013.0,
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class Environment(IEnvironment):
    def __init__(
        self,
        calendar: Calendar,
        world: Optional[IWorld] = None,
        season_strategy: Optional[ISeasonStrategy] = None,
        daynight_strategy: Optional[IDayNightStrategy] = None,
        weather_strategy: Optional[IWeatherStrategy] = None,
    ):
        self._calendar = calendar
        self._world = world
        self._season_strategy = season_strategy
        self._daynight_strategy = daynight_strategy
        self._weather_strategy = weather_strategy

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    @property
    def tick(self) -> int:
        return self._calendar.tick

    @property
    def calendar(self) -> ICalendar:
        return self._calendar

    @property
    def weather_strategy(self) -> Optional[IWeatherStrategy]:
        return self._weather_strategy

    @property
    def season_strategy(self) -> Optional[ISeasonStrategy]:
        return self._season_strategy

    @property
    def daynight_strategy(self) -> Optional[IDayNightStrategy]:
        return self._daynight_strategy

    def _reference_point(self):
        if self._world is not None:
            return self._world.width / 2.0, self._world.height / 2.0
        return 0.0, 0.0

    # ------------------------------------------------------------------
    # Aggregate readings (HUD)
    # ------------------------------------------------------------------
    @property
    def season(self) -> str:
        return self._calendar.season

    @property
    def phase(self) -> str:
        if self._daynight_strategy is None:
            return "day"
        return self._daynight_strategy.phase(self._calendar)

    @property
    def weather(self) -> str:
        if self._weather_strategy is None:
            return "clear"
        return self._weather_strategy.weather

    @property
    def light_level(self) -> float:
        x, y = self._reference_point()
        return self.light_at(x, y)

    @property
    def palette(self) -> SeasonPalette:
        if self._season_strategy is None:
            return _STATIC_PALETTE
        return self._season_strategy.palette(self._calendar)

    # ------------------------------------------------------------------
    # Positional readings
    # ------------------------------------------------------------------
    def weather_at(self, x: float, y: float) -> str:
        if self._weather_strategy is None:
            return "clear"
        return self._weather_strategy.weather_at(x, y)

    def light_at(self, x: float, y: float) -> float:
        if self._daynight_strategy is None:
            base = _STATIC_LIGHT
        else:
            base = self._daynight_strategy.light_at(self._calendar, x, y)

        dim = _WEATHER_LIGHT.get(self.weather_at(x, y), 1.0)
        return _clamp(base * dim, 0.0, 1.0)

    def humidity_at(self, x: float, y: float) -> float:
        pal = self.palette
        humidity = pal.humidity + _WEATHER_HUMIDITY.get(self.weather_at(x, y), 0.0)
        humidity += 0.05 * math.sin(x / 130.0) * math.cos(y / 110.0)
        return _clamp(humidity, 0.0, 1.0)

    def pressure_at(self, x: float, y: float) -> float:
        pal = self.palette
        pressure = pal.pressure_hpa + _WEATHER_PRESSURE_HPA.get(
            self.weather_at(x, y), 0.0
        )
        pressure += 1.5 * math.sin(x / 140.0) * math.cos(y / 120.0)
        return round(pressure, 1)

    def temperature_at(self, x: float, y: float) -> float:
        pal = self.palette
        light = self.light_at(x, y)

        temperature = pal.base_temperature + pal.temperature_swing * (2.0 * light - 1.0)
        temperature += _WEATHER_TEMP_C.get(self.weather_at(x, y), 0.0)

        # Smooth position-dependent variation (about +/- 3 C).
        microclimate = 2.2 * math.sin(x / 210.0) * math.cos(y / 170.0)
        microclimate += 0.8 * math.sin((x + y) / 95.0)
        temperature += microclimate

        return round(temperature, 1)

    # ------------------------------------------------------------------
    # Clock
    # ------------------------------------------------------------------
    def advance_tick(self) -> None:
        self._calendar.advance()
        if self._weather_strategy is not None:
            self._weather_strategy.update(self._calendar.tick, self)

    def reset(self) -> None:
        self._calendar.reset()
        if self._weather_strategy is not None:
            self._weather_strategy.reset()
