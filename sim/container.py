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
    CREATION_STRATEGY_NAMES,
    DAYNIGHT_STRATEGY_NAMES,
    ENERGY_STRATEGY_NAMES,
    MOVEMENT_STRATEGY_NAMES,
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
from sim.implementations.energy import FixedEnergyStrategy, PerDayEnergyStrategy
from sim.implementations.creation import (
    DensityBasedCreationStrategy,
    FixedAmountCreationStrategy,
)
from sim.implementations.daynight import DayNightStrategy
from sim.implementations.gender import GenderController
from sim.implementations.movement import StraightLineMovementStrategy
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
from sim.interfaces.energy import IEnergyStrategy
from sim.interfaces.barrier import IBarrierStrategy
from sim.interfaces.creation import IBeanCreationStrategy
from sim.interfaces.gender import IGenderController
from sim.interfaces.movement import IMovementStrategy
from sim.interfaces.environment import (
    IDayNightStrategy,
    ISeasonStrategy,
    IWeatherStrategy,
)
from sim.interfaces.placement import IPlacementStrategy, ISpawnController
from sim.observability import get_logger
from sim.random import init_random

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
        # Initialize global random generator first so all subsystems can use it
        init_random(config.random)
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
        self.creation_strategy: IBeanCreationStrategy = self._build_creation_strategy(
            config
        )
        self.spawn_controller: ISpawnController = self._build_spawn_controller(config)
        self.beans = self._spawn_beans()
        self.movement_strategy: IMovementStrategy = self._build_movement_strategy(
            config
        )
        self.energy_strategy: IEnergyStrategy = self._build_energy_strategy(config)
        # Assign genotypes to beans after spawning
        self._assign_genotypes()
        logger.info(
            "container.built world=%sx%s cells=%sx%s cell_size=%s tick_rate=%s "
            "seasons=%s strategies=%s/%s/%s barriers=%s placement=%s "
            "creation=%s movement=%s energy=%s beans=%s",
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
            config.creation.strategy_name,
            config.movement.strategy_name,
            config.energy.strategy_name,
            len(self.beans),
        )

    def _assign_genotypes(self) -> None:
        """Assign default genotype and phenotype to all beans."""
        from sim.domain.genotype import Genotype, create_default_phenotype

        for bean in self.beans:
            # Create genotype with the bean's gender-assigned color as base_color
            genotype = Genotype(
                energy_capacity=1000.0,
                metabolic_rate=1.0,
                drag_coefficient=0.01,
                max_speed=60.0,
                acceleration=30.0,
                base_color=bean.color,  # Use gender-assigned color
                dormant_color=(139, 69, 19),
            )
            bean.genotype = genotype
            bean.phenotype = create_default_phenotype(genotype)
            # Initialize velocity from movement strategy
            bean.phenotype.velocity = (bean.vx or 0.0, bean.vy or 0.0)
            # Update phenotype color from genotype (sets to base_color)
            bean.phenotype.update_color(genotype)
            # Sync bean color from phenotype
            bean.update_color_from_phenotype()

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

    def _build_creation_strategy(
        self, config: SimulationConfig
    ) -> IBeanCreationStrategy:
        cc = config.creation
        if cc.strategy_name == "density_based":
            return DensityBasedCreationStrategy(config.bean_placement)
        if cc.strategy_name == "fixed_amount":
            return FixedAmountCreationStrategy(
                config=cc.fixed_amount,
                placement_config=config.bean_placement,
            )
        raise ValueError(
            f"Unknown creation strategy {cc.strategy_name!r}. "
            f"Use one of: {sorted(CREATION_STRATEGY_NAMES)}"
        )

    def _build_spawn_controller(
        self, config: SimulationConfig
    ) -> ISpawnController:
        return SpawnController(
            world=self.world,
            session=self.session,
            creation_strategy=self.creation_strategy,
            placement_strategy=self.placement_strategy,
            gender_controller=self.gender_controller,
        )

    def _build_movement_strategy(
        self, config: SimulationConfig
    ) -> IMovementStrategy:
        mc = config.movement
        if mc.strategy_name == "straight_line":
            return StraightLineMovementStrategy(
                config=mc,
                bean_radius=config.bean_placement.bean_radius,
                world_width=self.world.width,
                world_height=self.world.height,
            )
        raise ValueError(
            f"Unknown movement strategy {mc.strategy_name!r}. "
            f"Use one of: {sorted(MOVEMENT_STRATEGY_NAMES)}"
        )

    def _build_energy_strategy(self, config: SimulationConfig) -> IEnergyStrategy:
        ec = config.energy
        if ec.strategy_name == "fixed":
            return FixedEnergyStrategy(config=ec)
        if ec.strategy_name == "per_day":
            return PerDayEnergyStrategy(config=ec)
        raise ValueError(
            f"Unknown energy strategy {ec.strategy_name!r}. "
            f"Use one of: {sorted(ENERGY_STRATEGY_NAMES)}"
        )

    def _spawn_beans(self) -> List:
        """Run the spawn controller and store resulting beans in the session."""
        beans = self.spawn_controller.spawn_beans()
        self.session.beans = beans
        # Track initial gender counts for census
        initial_female = sum(1 for b in beans if b.gender == "female")
        initial_male = sum(1 for b in beans if b.gender == "male")
        self.session.initial_female = initial_female
        self.session.initial_male = initial_male
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
