"""Density-based bean creation strategy.

This is the original behaviour: the population is derived from the world area,
the configured density tier and a stochastic variance. Positions, genders and
colours are still delegated to the configured strategies.
"""

from __future__ import annotations

import random
from typing import Dict, List

from sim.config import BEAN_DENSITY_COEFFICIENTS, BeanPlacementConfig
from sim.domain.beans import Bean, Position
from sim.domain.world import World
from sim.interfaces.creation import IBeanCreationStrategy
from sim.interfaces.gender import IGenderController
from sim.interfaces.placement import IPlacementStrategy
from sim.observability import get_logger, log_event

logger = get_logger("creation.density_based")


class DensityBasedCreationStrategy(IBeanCreationStrategy):
    name = "density_based"

    def __init__(self, config: BeanPlacementConfig):
        self.config = config

    def _target_population(self, area: float) -> int:
        """N = Round(area × density × (1 + Uniform(-variance, +variance)))."""
        rho = BEAN_DENSITY_COEFFICIENTS[self.config.density_tier]
        rng = random.Random(self.config.seed)
        variance = rng.uniform(-self.config.variance, self.config.variance)
        return max(0, round(area * rho * (1.0 + variance)))

    def create_beans(
        self,
        world: World,
        placement_strategy: IPlacementStrategy,
        gender_controller: IGenderController,
    ) -> List[Bean]:
        cfg = self.config
        area = float(world.width * world.height)
        target = self._target_population(area)

        log_event(
            logger,
            "spawn.started",
            strategy=cfg.strategy_name,
            creation_strategy=self.name,
            density_tier=cfg.density_tier,
            target_population=target,
            world_area=round(area, 2),
            variance=cfg.variance,
        )

        positions = placement_strategy.generate_positions(
            target,
            world.width,
            world.height,
            world=world,
            existing=[],
            radius=cfg.bean_radius,
        )
        log_event(
            logger,
            "spawn.positions_generated",
            requested=target,
            produced=len(positions),
            strategy=cfg.strategy_name,
        )

        beans = self._instantiate(positions, gender_controller)

        counts: Dict[str, int] = {}
        for bean in beans:
            counts[bean.gender] = counts.get(bean.gender, 0) + 1
        log_event(
            logger,
            "spawn.finished",
            beans=len(beans),
            target=target,
            creation_strategy=self.name,
            strategy=cfg.strategy_name,
            counts=",".join(f"{g}={c}" for g, c in sorted(counts.items())),
        )
        return beans

    @staticmethod
    def _instantiate(
        positions: List[Position], gender_controller: IGenderController
    ) -> List[Bean]:
        attributed = gender_controller.assign_attributes(positions)
        return [
            Bean(id=index, x=x, y=y, gender=gender, color=color)
            for index, ((x, y), gender, color) in enumerate(attributed, start=1)
        ]
