"""Spawn Controller.

Orchestrates the full bean initial-placement pipeline:

1. Load configuration (strategy, density tier, gender ratios, colors).
2. Calculate target population ``N`` from world area × density × variance.
3. Generate positions via the active :class:`IPlacementStrategy`.
4. Assign gender + color via the :class:`IGenderController`.
5. Instantiate :class:`sim.domain.beans.Bean` entities.

All placement strategies and gender controllers are resolved from config.
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

from sim.components import GameSession
from sim.config import (
    BEAN_DENSITY_COEFFICIENTS,
    BeanPlacementConfig,
    SimulationConfig,
)
from sim.domain.beans import Bean, Position, SpawnResult
from sim.domain.world import World
from sim.interfaces.gender import IGenderController
from sim.interfaces.placement import IPlacementStrategy, ISpawnController
from sim.observability import get_logger, log_event

logger = get_logger("spawn")


class SpawnController(ISpawnController):
    """Central orchestrator for initial bean placement."""

    def __init__(
        self,
        config: SimulationConfig,
        world: World,
        session: GameSession,
        placement_strategy: IPlacementStrategy,
        gender_controller: IGenderController,
    ):
        self.config = config
        self.world = world
        self.session = session
        self.placement = placement_strategy
        self.gender = gender_controller
        self.placement_config: BeanPlacementConfig = config.bean_placement
        self._beans: List[Bean] = []
        self._seed = self.placement_config.max_retry_limit  # seed base

    # ------------------------------------------------------------------
    # Step 2: area-based population calculus
    # ------------------------------------------------------------------
    def _world_area(self) -> float:
        """Rectangular arena area: A = width × height."""
        return float(self.world.width * self.world.height)

    def _target_population(self, area: float) -> int:
        """N = Round(A × ρ(density) × (1 + Uniform(-v, +v)))."""
        cfg = self.placement_config
        rho = BEAN_DENSITY_COEFFICIENTS[cfg.density_tier]
        rng = random.Random(self._seed)
        variance = rng.uniform(-cfg.variance, cfg.variance)
        n = round(area * rho * (1.0 + variance))
        return max(0, n)

    # ------------------------------------------------------------------
    # Step 6: instantiate beans
    # ------------------------------------------------------------------
    def spawn_beans(self) -> List[Bean]:
        """Run the full placement pipeline and return instantiated beans."""
        cfg = self.placement_config
        area = self._world_area()
        n = self._target_population(area)

        log_event(
            logger,
            "spawn.started",
            strategy=cfg.strategy_name,
            density_tier=cfg.density_tier,
            target_population=n,
            world_area=round(area, 2),
            variance=cfg.variance,
        )

        # Step 3: generate positions via the active placement strategy.
        positions = self.placement.generate_positions(
            n, self.world.width, self.world.height
        )
        log_event(
            logger,
            "spawn.positions_generated",
            requested=n,
            produced=len(positions),
            strategy=cfg.strategy_name,
        )

        # Steps 4-5: assign gender + color via the gender controller.
        attributed = self.gender.assign_attributes(positions)
        log_event(
            logger,
            "spawn.attributes_assigned",
            count=len(attributed),
            genders=",".join(f"{g}:{c}" for _, g, c in attributed),
        )

        # Step 6: instantiate Bean entities.
        beans: List[Bean] = []
        for index, (position, gender, color) in enumerate(attributed, start=1):
            x, y = position
            # Clamp into world bounds defensively.
            x = max(0.0, min(self.world.width, x))
            y = max(0.0, min(self.world.height, y))
            beans.append(Bean(id=index, x=x, y=y, gender=gender, color=color))

        self._beans = beans
        result = SpawnResult(
            beans=tuple(beans),
            target_population=n,
            actual_population=len(beans),
            world_area=area,
            density_coefficient=BEAN_DENSITY_COEFFICIENTS[cfg.density_tier],
            variance=cfg.variance,
            strategy_name=cfg.strategy_name,
        )
        log_event(
            logger,
            "spawn.finished",
            beans=len(beans),
            target=n,
            strategy=cfg.strategy_name,
            male=sum(1 for b in beans if b.gender == "male"),
            female=sum(1 for b in beans if b.gender == "female"),
        )
        return beans

    @property
    def beans(self) -> List[Bean]:
        return list(self._beans)
