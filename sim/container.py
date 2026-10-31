"""Dependency injection container.

Wires configuration into concrete domain objects.

Build order matters: the world provides the cell grid used by weather, and the
calendar needs the configured season names. Season and day/night are siblings
that both read the calendar; neither owns the other.
"""

from typing import Optional, Type, Union

from sim.components import GameSession
from sim.config import SimulationConfig
from sim.domain.calendar import Calendar
from sim.domain.environment import Environment
from sim.domain.session import GameSession as ConcreteGameSession
from sim.domain.world import World
from sim.implementations.daynight import DayNightStrategy
from sim.implementations.season import SeasonStrategy
from sim.implementations.weather import WeatherStrategy
from sim.interfaces.environment import (
    IDayNightStrategy,
    ISeasonStrategy,
    IWeatherStrategy,
)

_DAYNIGHT_NAMES = {"daynight", "daynightstrategy", "default"}
_SEASON_NAMES = {"season", "seasonstrategy", "default"}
_WEATHER_NAMES = {"weather", "weatherstrategy", "default"}

Strategy = Union[IWeatherStrategy, ISeasonStrategy, IDayNightStrategy]


class Container:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.world = self._build_world(config)
        self.calendar = self._build_calendar(config)
        self.environment = self._build_environment(config)
        self.session = self._build_session()
        self.debug = config.debug

    # ------------------------------------------------------------------
    # World
    # ------------------------------------------------------------------
    def _build_world(self, config: SimulationConfig) -> World:
        wc = config.world
        return World(
            width=wc.width,
            height=wc.height,
            cell_size=wc.cell_size,
            orientation=wc.orientation,
            wrap_around=wc.wrap_around,
        )

    # ------------------------------------------------------------------
    # Calendar
    # ------------------------------------------------------------------
    def _season_names(self, config: SimulationConfig):
        names = [season.name for season in config.seasons]
        return names or ["Spring"]

    def _build_calendar(self, config: SimulationConfig) -> Calendar:
        return Calendar(
            ticks_per_day=config.time.ticks_per_day,
            ticks_per_season=config.time.ticks_per_season,
            season_names=self._season_names(config),
            start_tick=config.time.start_tick,
        )

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve(name: Optional[str], aliases: set, label: str) -> bool:
        if name is None:
            return False
        if name.strip().lower() not in aliases:
            raise ValueError(
                f"Unknown {label} strategy {name!r}. "
                "Use None or one of: " + ", ".join(sorted(aliases))
            )
        return True

    def _build_environment(self, config: SimulationConfig) -> Environment:
        ec = config.environment

        season: Optional[ISeasonStrategy] = None
        if self._resolve(ec.season_strategy, _SEASON_NAMES, "season"):
            season = SeasonStrategy(
                seasons=config.seasons,
                ticks_per_season=config.time.ticks_per_season,
            )

        daynight: Optional[IDayNightStrategy] = None
        if self._resolve(ec.daynight_strategy, _DAYNIGHT_NAMES, "day/night"):
            daynight = DayNightStrategy(
                config=config.daynight,
                ticks_per_day=config.time.ticks_per_day,
            )

        weather: Optional[IWeatherStrategy] = None
        if self._resolve(ec.weather_strategy, _WEATHER_NAMES, "weather"):
            weather = WeatherStrategy(config=config.weather, world=self.world)

        return Environment(
            calendar=self.calendar,
            world=self.world,
            season_strategy=season,
            daynight_strategy=daynight,
            weather_strategy=weather,
        )

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------
    def _build_session(self) -> GameSession:
        return ConcreteGameSession(
            state=self.session_state_default(),
            world=self.world,
            environment=self.environment,
        )

    @staticmethod
    def session_state_default():
        from sim.components import GameState

        return GameState.START
