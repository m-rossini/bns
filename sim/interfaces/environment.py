"""Environment interfaces.

Responsibilities are split into siblings that all read the calendar:

    Calendar        tick -> day / clock / season / year (single time authority)
    ISeasonStrategy season parameters + palette for the current season
    IDayNightStrategy light, sky palette and sun/moon positions
    IWeatherStrategy  per-cell weather field
    IEnvironment      composes them into per-position readings

`None` for a strategy means "static": the environment keeps running but the
corresponding values stay at documented defaults.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple

from sim.domain.climate import ClimateContext
from sim.domain.visuals import CelestialState, SeasonPalette, SkyPalette, SolarProfile


class ICalendar(ABC):
    @property
    @abstractmethod
    def tick(self) -> int:
        ...

    @property
    @abstractmethod
    def day(self) -> int:
        ...

    @property
    @abstractmethod
    def day_fraction(self) -> float:
        ...

    @property
    @abstractmethod
    def clock(self) -> str:
        ...

    @property
    @abstractmethod
    def season(self) -> str:
        ...

    @property
    @abstractmethod
    def season_index(self) -> int:
        ...

    @property
    @abstractmethod
    def season_progress(self) -> float:
        ...

    @property
    @abstractmethod
    def day_of_season(self) -> int:
        ...

    @property
    @abstractmethod
    def year(self) -> int:
        ...

    @abstractmethod
    def advance(self, ticks: int = 1) -> None:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...


class ISeasonStrategy(ABC):
    @property
    @abstractmethod
    def ticks_per_season(self) -> int:
        ...

    @property
    @abstractmethod
    def season_names(self) -> Tuple[str, ...]:
        ...

    @abstractmethod
    def palette(self, calendar: ICalendar) -> SeasonPalette:
        """Appearance and physical baseline for the current season."""

    @abstractmethod
    def solar_profile(self, calendar: ICalendar) -> SolarProfile:
        """How much sun the world gets at this moment.

        The season strategy owns this value: it is the single input the
        day/night and weather strategies use to derive light and temperature.
        """

    @abstractmethod
    def get_season_name(self, calendar: ICalendar) -> str:
        """Return the name of the current season from the strategy perspective."""

    @abstractmethod
    def weather_weights(self, season: str) -> dict:
        ...


class IDayNightStrategy(ABC):
    @property
    @abstractmethod
    def ticks_per_day(self) -> int:
        ...

    @abstractmethod
    def light_at(
        self,
        calendar: ICalendar,
        x: float,
        y: float,
        solar: Optional[SolarProfile] = None,
    ) -> float:
        """Light level 0..1 at a world position (sun altitude + local shade).

        ``solar`` is the season's `SolarProfile`; it decides the day length and
        the peak intensity. ``None`` falls back to a neutral profile.
        """

    @abstractmethod
    def phase(
        self, calendar: ICalendar, solar: Optional[SolarProfile] = None
    ) -> str:
        ...

    @abstractmethod
    def celestial(
        self, calendar: ICalendar, solar: Optional[SolarProfile] = None
    ) -> CelestialState:
        ...

    @abstractmethod
    def sky_palette(self) -> SkyPalette:
        ...


class IWeatherStrategy(ABC):
    @property
    @abstractmethod
    def weather(self) -> str:
        """Representative condition (used for the aggregate HUD reading)."""

    @abstractmethod
    def weather_at(self, x: float, y: float) -> str:
        """Condition for the cell containing (x, y)."""

    @abstractmethod
    def weather_at_cell(self, col: int, row: int) -> str:
        ...

    @abstractmethod
    def update(self, tick: int, climate: ClimateContext) -> None:
        """Rebuild the field from the current climate snapshot."""

    @abstractmethod
    def reset(self) -> None:
        ...


class IEnvironment(ABC):
    @property
    @abstractmethod
    def tick(self) -> int:
        ...

    @property
    @abstractmethod
    def calendar(self) -> ICalendar:
        ...

    @property
    @abstractmethod
    def weather_strategy(self) -> Optional[IWeatherStrategy]:
        ...

    @property
    @abstractmethod
    def season_strategy(self) -> Optional[ISeasonStrategy]:
        ...

    @property
    @abstractmethod
    def daynight_strategy(self) -> Optional[IDayNightStrategy]:
        ...

    @property
    @abstractmethod
    def season(self) -> str:
        ...

    @property
    @abstractmethod
    def phase(self) -> str:
        ...

    @property
    @abstractmethod
    def weather(self) -> str:
        ...

    @property
    @abstractmethod
    def light_level(self) -> float:
        ...

    @property
    @abstractmethod
    def palette(self) -> SeasonPalette:
        ...

    @property
    @abstractmethod
    def solar(self) -> SolarProfile:
        """Sun delivered by the current season (owned by the season strategy)."""

    @property
    @abstractmethod
    def celestial(self) -> CelestialState:
        ...

    @abstractmethod
    def climate_context(self) -> ClimateContext:
        """Immutable climate snapshot handed to the weather strategy."""

    @abstractmethod
    def weather_at(self, x: float, y: float) -> str:
        ...

    @abstractmethod
    def humidity_at(self, x: float, y: float) -> float:
        ...

    @abstractmethod
    def pressure_at(self, x: float, y: float) -> float:
        ...

    @abstractmethod
    def temperature_at(self, x: float, y: float) -> float:
        ...

    @abstractmethod
    def advance_tick(self) -> None:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...
