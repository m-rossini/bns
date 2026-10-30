"""Dependency injection container.

Wires configuration into concrete domain objects. Environment strategies are
resolved by name from the config; ``None`` leaves that strategy disabled.
"""

from typing import Optional, Type, Union

from sim.components import Barrier, GameSession
from sim.config import EnvironmentConfig, SimulationConfig, WorldConfig
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


class Container:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.world = self._build_world(config.world)
        self.environment = self._build_environment(config.environment)
        self.session = self._build_session()
        self.debug = config.debug

    def _build_world(self, wc: WorldConfig) -> World:
        world = World(
            width=wc.width,
            height=wc.height,
            orientation=wc.orientation,
            wrap_around=wc.wrap_around,
        )
        for bc in wc.barriers:
            world.add_barrier(
                Barrier(
                    id=bc.id,
                    kind=bc.kind,
                    x=bc.x,
                    y=bc.y,
                    width=bc.width,
                    height=bc.height,
                    radius=bc.radius,
                )
            )
        return world

    @staticmethod
    def _resolve(
        name: Optional[str],
        aliases: set,
        strategy_type: Type,
        label: str,
    ) -> Optional[Union[IWeatherStrategy, ISeasonStrategy, IDayNightStrategy]]:
        if name is None:
            return None
        if name.strip().lower() not in aliases:
            raise ValueError(
                f"Unknown {label} strategy {name!r}. "
                "Use None or one of: " + ", ".join(sorted(aliases))
            )
        return strategy_type()

    def _build_environment(self, ec: EnvironmentConfig) -> Environment:
        weather = self._resolve(
            ec.weather_strategy, _WEATHER_NAMES, WeatherStrategy, "weather"
        )
        season = self._resolve(
            ec.season_strategy, _SEASON_NAMES, SeasonStrategy, "season"
        )
        daynight = self._resolve(
            ec.daynight_strategy, _DAYNIGHT_NAMES, DayNightStrategy, "day/night"
        )
        return Environment(
            weather_strategy=weather,
            season_strategy=season,
            daynight_strategy=daynight,
        )

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
