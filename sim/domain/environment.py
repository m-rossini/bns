"""Concrete Environment implementation.

Composes the calendar and the three optional strategies. Every environmental
reading is a function of position:

* ``weather_at(x, y)``     — per-cell weather field
* ``solar``               — the season's `SolarProfile` (owner of the sun)
* ``light_at(x, y)``       — sun arc * season intensity * shading * weather * gradient
* ``humidity_at(x, y)``    — seasonal baseline + weather + climate gradient + noise
* ``pressure_at(x, y)``    — seasonal baseline + weather + climate gradient + noise
* ``temperature_at(x, y)`` — seasonal mean + diurnal light + weather + gradient + microclimate
* ``climate_context()``    — immutable snapshot for the weather strategy

The gradient direction comes from `WorldConfig.orientation` unless a
`GradientConfig` overrides it. This is what makes two cells in the same season
read differently, and it is fully configuration-driven (see `EnvironmentConfig`).

With a strategy set to ``None`` the environment still runs, and that reading
falls back to a documented constant ("static" mode).
"""

import logging
import math
from typing import Optional

from sim.config import EnvironmentConfig, LoggingConfig, WeatherConfig
from sim.domain.calendar import Calendar
from sim.domain.climate import DEFAULT_WEATHER_WEIGHTS, ClimateContext
from sim.domain.gradient import Gradient
from sim.domain.visuals import CelestialState, SeasonPalette, SolarProfile
from sim.interfaces.environment import (
    ICalendar,
    IDayNightStrategy,
    IEnvironment,
    ISeasonStrategy,
    IWeatherStrategy,
)
from sim.interfaces.world import IWorld
from sim.observability import EventLog, get_logger, log_event

logger = get_logger("environment")

_STATIC_LIGHT = 0.7
_STATIC_SOLAR = SolarProfile()
_STATIC_CELESTIAL = CelestialState(
    sun_progress=0.5,
    moon_progress=0.0,
    sun_visible=True,
    moon_visible=False,
    moon_illumination=0.0,
)
_STATIC_PALETTE = SeasonPalette(
    name="Static",
    ground=(110, 150, 110),
    details=((140, 170, 140),),
    base_temperature=14.0,
    temperature_swing=7.0,
    humidity=0.5,
    pressure_hpa=1013.0,
    sun_intensity=1.0,
    daylight_fraction=0.5,
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
        environment_config: Optional[EnvironmentConfig] = None,
        weather_config: Optional[WeatherConfig] = None,
        logging_config: Optional[LoggingConfig] = None,
    ):
        self._calendar = calendar
        self._world = world
        self._season_strategy = season_strategy
        self._daynight_strategy = daynight_strategy
        self._weather_strategy = weather_strategy

        self._env_config = environment_config or EnvironmentConfig()
        self._weather_config = weather_config or WeatherConfig()
        logging_config = logging_config or LoggingConfig()

        fallback = world.orientation if world is not None else "north_south"

        def gradient(spec) -> Gradient:
            return Gradient(
                orientation=spec.orientation or fallback,
                start=spec.start,
                end=spec.end,
            )

        self._temperature_gradient = gradient(self._env_config.temperature_gradient)
        self._humidity_gradient = gradient(self._env_config.humidity_gradient)
        self._pressure_gradient = gradient(self._env_config.pressure_gradient)
        self._light_gradient = gradient(self._env_config.light_gradient)

        self._event_log = EventLog("environment", enabled=logging_config.business)
        self._readings_enabled = logging_config.readings
        self._readings_interval = max(1, logging_config.readings_interval)

        self._last_day = calendar.day
        self._last_season = calendar.season
        self._last_weather = self.weather
        self._last_tick = calendar.tick
        self._palette_tick: Optional[int] = None
        self._palette_cache: SeasonPalette = _STATIC_PALETTE
        self._solar_cache: SolarProfile = _STATIC_SOLAR

        logger.debug(
            "environment.created cols=%s rows=%s season_strategy=%s "
            "daynight_strategy=%s weather_strategy=%s gradients=%s/%s/%s/%s",
            getattr(world, "cols", None),
            getattr(world, "rows", None),
            type(season_strategy).__name__ if season_strategy else None,
            type(daynight_strategy).__name__ if daynight_strategy else None,
            type(weather_strategy).__name__ if weather_strategy else None,
            self._temperature_gradient.orientation,
            self._humidity_gradient.orientation,
            self._pressure_gradient.orientation,
            self._light_gradient.orientation,
        )

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
    def config(self) -> EnvironmentConfig:
        return self._env_config

    @property
    def weather_config(self) -> WeatherConfig:
        return self._weather_config

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

    def _extent(self):
        if self._world is None:
            return 1.0, 1.0
        return max(1.0, self._world.width), max(1.0, self._world.height)

    def _position(self, x: float, y: float) -> float:
        """Normalised gradient position (0..1) for readings."""
        width, height = self._extent()
        return self._temperature_gradient.factor(x, y, width, height)

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
        return self._daynight_strategy.phase(self._calendar, self.solar)

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
    def solar(self) -> SolarProfile:
        if self._season_strategy is None:
            return _STATIC_SOLAR
        tick = self._calendar.tick
        if tick != self._palette_tick:
            self._solar_cache = self._season_strategy.solar_profile(self._calendar)
            self._palette_cache = self._season_strategy.palette(self._calendar)
            self._palette_tick = tick
        return self._solar_cache

    @property
    def celestial(self) -> CelestialState:
        if self._daynight_strategy is None:
            return _STATIC_CELESTIAL
        return self._daynight_strategy.celestial(self._calendar, self.solar)

    @property
    def palette(self) -> SeasonPalette:
        if self._season_strategy is None:
            return _STATIC_PALETTE
        tick = self._calendar.tick
        if tick != self._palette_tick:
            self._solar_cache = self._season_strategy.solar_profile(self._calendar)
            self._palette_cache = self._season_strategy.palette(self._calendar)
            self._palette_tick = tick
        return self._palette_cache

    def weather_weights(self) -> dict:
        """Season weights before the climate adjustments, for the HUD/debug."""
        if self._season_strategy is None:
            return {}
        return self._season_strategy.weather_weights(self._calendar.season)

    def climate_context(self) -> ClimateContext:
        """Snapshot handed to the weather strategy on every tick."""
        palette = self.palette
        weights = self.weather_weights()
        if not weights:
            weights = dict(DEFAULT_WEATHER_WEIGHTS)
        return ClimateContext.from_palette(
            tick=self._calendar.tick,
            season=self._calendar.season,
            season_progress=self._calendar.season_progress,
            palette=palette,
            solar=self.solar,
            weather_weights=weights,
            world=self._world,
        )

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
            base = self._daynight_strategy.light_at(
                self._calendar, x, y, solar=self.solar
            )

        width, height = self._extent()
        gradient = self._light_gradient.value(x, y, width, height)
        dim = self._weather_config.light_factors.get(self.weather_at(x, y), 1.0)
        return _clamp(base * gradient * dim, 0.0, 1.0)

    def humidity_at(self, x: float, y: float) -> float:
        palette = self.palette
        width, height = self._extent()
        humidity = palette.humidity
        humidity += self._weather_config.humidity_offsets.get(
            self.weather_at(x, y), 0.0
        )
        humidity += self._humidity_gradient.value(x, y, width, height)
        noise = 0.05 * self._env_config.microclimate
        humidity += noise * math.sin(x / 130.0) * math.cos(y / 110.0)
        return _clamp(humidity, 0.0, 1.0)

    def pressure_at(self, x: float, y: float) -> float:
        palette = self.palette
        width, height = self._extent()
        pressure = palette.pressure_hpa
        pressure += self._weather_config.pressure_offsets.get(
            self.weather_at(x, y), 0.0
        )
        pressure += self._pressure_gradient.value(x, y, width, height)
        noise = 1.5 * self._env_config.microclimate
        pressure += noise * math.sin(x / 140.0) * math.cos(y / 120.0)
        return round(pressure, 1)

    def temperature_at(self, x: float, y: float) -> float:
        palette = self.palette
        width, height = self._extent()
        light = self.light_at(x, y)

        temperature = palette.base_temperature + palette.temperature_swing * (
            2.0 * light - 1.0
        )
        temperature += self._weather_config.temperature_offsets.get(
            self.weather_at(x, y), 0.0
        )
        temperature += self._temperature_gradient.value(x, y, width, height)

        # Fine-grained variation so neighbouring cells differ even inside one
        # weather front; scaled by `EnvironmentConfig.microclimate`.
        amount = self._env_config.microclimate
        microclimate = 2.2 * amount * math.sin(x / 210.0) * math.cos(y / 170.0)
        microclimate += 0.8 * amount * math.sin((x + y) / 95.0)
        temperature += microclimate

        return round(temperature, 1)

    # ------------------------------------------------------------------
    # Clock
    # ------------------------------------------------------------------
    def advance_tick(self) -> None:
        self._calendar.advance()
        if self._weather_strategy is not None:
            self._weather_strategy.update(
                self._calendar.tick, self.climate_context()
            )

        tick = self._calendar.tick
        day = self._calendar.day
        season = self._calendar.season
        weather = self.weather

        if day != self._last_day:
            self._event_log.event(
                "environment.day_changed",
                day=day,
                season=season,
                clock=self._calendar.clock,
                year=self._calendar.year,
            )
            self._last_day = day

        if season != self._last_season:
            self._event_log.event(
                "environment.season_changed",
                previous=self._last_season,
                season=season,
                day=day,
                year=self._calendar.year,
                ticks_per_season=self._calendar.ticks_per_season,
            )
            self._last_season = season

        if weather != self._last_weather:
            self._event_log.event(
                "environment.weather_changed",
                previous=self._last_weather,
                weather=weather,
                season=season,
                tick=tick,
            )
            self._last_weather = weather

        if (
            self._readings_enabled
            and logger.isEnabledFor(logging.DEBUG)
            and tick - self._last_tick >= self._readings_interval
        ):
            self._log_reading(tick, day, season, weather)
            self._last_tick = tick

    def _log_reading(self, tick: int, day: int, season: str, weather: str) -> None:
        if not logger.isEnabledFor(logging.DEBUG):
            return
        x, y = self._reference_point()
        log_event(
            logger,
            "environment.reading",
            level=logging.DEBUG,
            tick=tick,
            day=day,
            clock=self._calendar.clock,
            season=season,
            phase=self.phase,
            weather=weather,
            temperature=self.temperature_at(x, y),
            humidity=self.humidity_at(x, y),
            pressure=self.pressure_at(x, y),
            light=self.light_at(x, y),
            gradient_position=self._position(x, y),
        )

    def reset(self) -> None:
        self._calendar.reset()
        if self._weather_strategy is not None:
            self._weather_strategy.reset()
        self._last_day = self._calendar.day
        self._last_season = self._calendar.season
        self._last_weather = self.weather
        self._last_tick = self._calendar.tick
        self._palette_tick = None
        self._palette_cache = _STATIC_PALETTE
        self._solar_cache = _STATIC_SOLAR
        self._event_log.event("environment.reset", tick=self._calendar.tick)
