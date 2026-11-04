"""Fixed-amount bean creation strategy.

Creates exactly the configured number of beans, independent of world area or
density tiers. The *positions* still come from the configured placement
strategy; this strategy only overrides the population size.
"""

from __future__ import annotations

import math
from typing import Dict, List

from sim.config import BeanPlacementConfig, FixedAmountCreationConfig
from sim.domain.beans import Bean, Position
from sim.domain.world import World
from sim.interfaces.creation import IBeanCreationStrategy
from sim.interfaces.gender import IGenderController
from sim.interfaces.placement import IPlacementStrategy
from sim.observability import get_logger, log_event

logger = get_logger("creation.fixed_amount")


class FixedAmountCreationStrategy(IBeanCreationStrategy):
    name = "fixed_amount"

    def __init__(
        self,
        config: FixedAmountCreationConfig,
        placement_config: BeanPlacementConfig,
    ):
        self.config = config
        self.placement_config = placement_config

    def create_beans(
        self,
        world: World,
        placement_strategy: IPlacementStrategy,
        gender_controller: IGenderController,
    ) -> List[Bean]:
        total = self.config.total_beans
        cfg = self.placement_config
        radius = cfg.bean_radius

        log_event(
            logger,
            "spawn.started",
            strategy=cfg.strategy_name,
            creation_strategy=self.name,
            target_population=total,
        )

        positions: List[Position] = []
        # Placement strategies derive their spacing from the requested count.
        # Asking for more candidates than we need (and trimming) lets us reach
        # the exact total while keeping the collision-free guarantee.
        overshoot = self.config.placement_overshoot
        for batch in range(self.config.max_batches):
            remaining = total - len(positions)
            if remaining <= 0:
                break
            request = max(remaining, int(math.ceil(total * overshoot)))
            produced = placement_strategy.generate_positions(
                request,
                world.width,
                world.height,
                world=world,
                existing=positions,
                radius=radius,
            )
            if not produced:
                break
            positions.extend(produced[:remaining])
            log_event(
                logger,
                "spawn.positions_batch",
                batch=batch + 1,
                requested=request,
                produced=len(produced),
                total=len(positions),
            )
            overshoot *= 2

        if len(positions) < total:
            log_event(
                logger,
                "spawn.shortfall",
                requested=total,
                produced=len(positions),
                creation_strategy=self.name,
            )

        beans = self._instantiate(positions, gender_controller)

        counts: Dict[str, int] = {}
        for bean in beans:
            counts[bean.gender] = counts.get(bean.gender, 0) + 1
        log_event(
            logger,
            "spawn.finished",
            beans=len(beans),
            target=total,
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
