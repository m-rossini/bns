"""Dependency injection container.

Wires configuration into concrete domain objects.

Build order matters: the world provides the cell grid used by weather, and the
calendar needs the configured season names. Season and day/night are siblings
that both read the calendar; neither owns the other.
"""

from typing import List, Optional, Type, Union

from sim.components import GameSession
from sim.config import (
    BEAN_DENSITY_THRESHOLDS,
    DAYNIGHT_STRATEGY_NAMES,
    PLACEMENT_STRATEGY_NAMES,
    SEASON_STRATEGY_NAMES,
    SimulationConfig,
    WEATHER_STRATEGY_NAMES,
)
from sim.domain.calendar import Calendar
from sim.domain.environment import Environment
from sim.domain.session import GameSession as ConcreteGameSession
from sim.domain.spawn_controller import SpawnController
from sim.domain.world import World
from sim.implementations.barrier import BarrierStrategy
from sim.implementations.daynight import DayNightStrategy
from sim.implementations.gender import GenderController
from sim.implementations.placement import (
    BorderToCenterStrategy,
    CenterToBorderStrategy,
    ColonyClusterStrategy,
    LinearGradientStrategy,
    PoissonDiscStrategy,
    ResourceGradientStrategy,
    SymmetricalStrategy,
)
from sim.implementations.season import SeasonStrategy
from sim.implementations.weather import WeatherStrategy
from sim.interfaces.barrier import IBarrierStrategy
from sim.interfaces.gender import IGenderController
from sim.interfaces.environment import (
    IDayNightStrategy,
    ISeasonStrategy,
    IWeatherStrategy,
)
from sim.interfaces.placement import IPlacementStrategy, ISpawnController
from sim.observability import get_logger

logger = get_logger("container")

#: Name -> strategy class wiring for placement strategies (DI wiring; the
#: valid names live in config.PLACEMENT_STRATEGY_NAMES).
_PLACEMENT_CLASSES = {
    "poisson_disc": PoissonDiscStrategy,
    "symmetrical": SymmetricalStrategy,
    "colony_cluster": ColonyClusterStrategy,
    "center_to_border": CenterToBorderStrategy,
    "border_to_center": BorderToCenterStrategy,
    "linear_gradient": LinearGradientStrategy,
    "resource_gradient": ResourceGradientStrategy,
}

Strategy = Union[IWeatherStrategy, ISeasonStrategy, IDayNightStrategy]


class Container:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.barrier_strategy: IBarrierStrategy = BarrierStrategy(config.barriers)
        self.world = self._build_world(config)
        self.calendar = self._build_calendar(config)
        self.environment = self._build_environment(config)
        self.session = self._build_session()
        self.debug = config.debug
        self._place_barriers()
        self.placement_strategy: IPlacementStrategy = self._build_placement_strategy(
            config
        )
        self.gender_controller: IGenderController = self._build_gender_controller(
            config
        )
        self.spawn_controller: ISpawnController = self._build_spawn_controller(config)
        self.beans = self._spawn_beans()
        logger.info(
            "container.built world=%sx%s cells=%sx%s cell_size=%s tick_rate=%s "
            "seasons=%s strategies=%s/%s/%s barriers=%s placement=%s beans=%s",
            self.world.width,
            self.world.height,
            self.world.cols,
            self.world.rows,
            self.world.cell_size,
            config.tick_rate,
            self.calendar.season_names,
            config.environment.season_strategy,
            config.environment.daynight_strategy,
            config.environment.weather_strategy,
            len(self.world.barriers),
            config.bean_placement.strategy_name,
            len(self.beans),
        )

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
            barrier_strategy=self.barrier_strategy,
        )

    def _place_barriers(self) -> None:
        """Generate and register the strategy's barriers (validated by it)."""
        for barrier in self.barrier_strategy.create_barriers(self.world):
            self.world.add_barrier(barrier)

    # ------------------------------------------------------------------
    # Bean placement
    # ------------------------------------------------------------------
    def _build_placement_strategy(
        self, config: SimulationConfig
    ) -> IPlacementStrategy:
        bp = config.bean_placement
        strategy_name = bp.strategy_name
        configs = {
            "poisson_disc": bp.poisson_disc,
            "symmetrical": bp.symmetrical,
            "colony_cluster": bp.colony_cluster,
            "center_to_border": bp.center_to_border,
            "border_to_center": bp.border_to_center,
            "linear_gradient": bp.linear_gradient,
            "resource_gradient": bp.resource_gradient,
        }
        cls = _PLACEMENT_CLASSES.get(strategy_name)
        if cls is None:
            raise ValueError(
                f"Unknown placement strategy {strategy_name!r}. "
                f"Use one of: {sorted(PLACEMENT_STRATEGY_NAMES)}"
            )
        cfg = configs[strategy_name]
        return cls(config=cfg, seed=bp.seed)

    def _build_gender_controller(
        self, config: SimulationConfig
    ) -> IGenderController:
        return GenderController(config.bean_placement)

    def _build_spawn_controller(
        self, config: SimulationConfig
    ) -> ISpawnController:
        return SpawnController(
            config=config,
            world=self.world,
            session=self.session,
            placement_strategy=self.placement_strategy,
            gender_controller=self.gender_controller,
        )

    def _spawn_beans(self) -> List:
        """Run the spawn controller and store resulting beans in the session."""
        beans = self.spawn_controller.spawn_beans()
        self.session.beans = beans
        return beans

    # ------------------------------------------------------------------
    # Calendar
    # ------------------------------------------------------------------
    def _season_names(self, config: SimulationConfig):
        names = [season.name for season in config.seasons]
        if not names:
            raise ValueError(
                "config.seasons must contain at least one season; "
                "season names are mandatory (no default fallback)"
            )
        return names

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
        if self._resolve(ec.season_strategy, SEASON_STRATEGY_NAMES, "season"):
            season = SeasonStrategy(
                seasons=config.seasons,
                ticks_per_season=config.time.ticks_per_season,
            )

        daynight: Optional[IDayNightStrategy] = None
        if self._resolve(ec.daynight_strategy, DAYNIGHT_STRATEGY_NAMES, "day/night"):
            daynight = DayNightStrategy(
                config=config.daynight,
                ticks_per_day=config.time.ticks_per_day,
            )

        weather: Optional[IWeatherStrategy] = None
        if self._resolve(ec.weather_strategy, WEATHER_STRATEGY_NAMES, "weather"):
            weather = WeatherStrategy(config=config.weather, world=self.world)

        return Environment(
            calendar=self.calendar,
            world=self.world,
            season_strategy=season,
            daynight_strategy=daynight,
            weather_strategy=weather,
            environment_config=config.environment,
            weather_config=config.weather,
            logging_config=config.logging,
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
