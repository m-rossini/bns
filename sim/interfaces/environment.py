"""Interface for the environment aggregator.

The environment holds the tick clock and optional strategy references
(weather, season, day-night) and derives values such as temperature.
"""

from abc import ABC, abstractmethod
from typing import Optional


class IWeatherStrategy(ABC):
    @property
    @abstractmethod
    def weather(self) -> str:
        """Current weather condition (clear, cloudy, rain, storm, snow)."""

    @abstractmethod
    def update(self, tick: int, environment: "IEnvironment") -> None:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...


class ISeasonStrategy(ABC):
    @property
    @abstractmethod
    def ticks_per_season(self) -> int:
        ...

    @abstractmethod
    def get_season(self, tick: int) -> str:
        ...


class IDayNightStrategy(ABC):
    @property
    @abstractmethod
    def ticks_per_day(self) -> int:
        ...

    @abstractmethod
    def get_light_level(self, tick: int) -> float:
        ...

    @abstractmethod
    def get_phase(self, tick: int) -> str:
        ...


class IEnvironment(ABC):
    @property
    @abstractmethod
    def tick(self) -> int:
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
    def weather(self) -> str:
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
    def light_level(self) -> float:
        ...

    @abstractmethod
    def temperature_at(self, x: float, y: float) -> float:
        """Temperature in Celsius at a world position."""
        ...

    @abstractmethod
    def advance_tick(self) -> None:
        ...

    @abstractmethod
    def reset(self) -> None:
        """Return the environment to its initial state (tick 0)."""
        ...
