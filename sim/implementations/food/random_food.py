"""Random food spawn strategy: uniform morsels with random energy.

Morsels land anywhere in the world (on barriers or beans if chance puts them
there) with energy drawn uniformly from ``[min_morsel_energy,
max_morsel_energy]``. The initial seeding sums to ``initial_total_energy``;
later top-ups cover the deficit to ``target_total_energy × abundance`` on
``top_up_interval_ticks`` boundaries, capped by ``max_items``. Snapshots store
the food list, so a resumed run keeps its exact morsels; ids restart from the
current maximum, so top-ups after a restore never collide.
"""

import random
from typing import List

from sim.config import FoodConfig
from sim.domain.food import Food, total_energy
from sim.interfaces.food import IFoodSpawnStrategy
from sim.interfaces.world import IWorld
from sim.observability import get_logger

logger = get_logger("food.random")


class RandomFoodSpawnStrategy(IFoodSpawnStrategy):
    def __init__(self, config: FoodConfig):
        self._config = config
        self._rng = random.Random(config.seed)

    # ------------------------------------------------------------------
    # Placement
    # ------------------------------------------------------------------
    def _position(self, world: IWorld) -> tuple:
        config = self._config
        margin = min(config.margin_cells * world.cell_size, world.width / 4.0)
        x = self._rng.uniform(margin, max(margin, world.width - margin))
        margin_y = min(config.margin_cells * world.cell_size, world.height / 4.0)
        y = self._rng.uniform(margin_y, max(margin_y, world.height - margin_y))
        return x, y

    def _morsel(self, world: IWorld, food_id: int, energy: float) -> Food:
        x, y = self._position(world)
        return Food(
            id=food_id,
            x=x,
            y=y,
            radius=self._config.food_radius,
            energy=energy,
            initial_energy=energy,
        )

    def _morsel_energy(self) -> float:
        config = self._config
        return self._rng.uniform(
            config.min_morsel_energy, config.max_morsel_energy
        )

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------
    def initial_food(self, world: IWorld) -> List[Food]:
        config = self._config
        foods: List[Food] = []
        covered = 0.0
        while covered < config.initial_total_energy and len(foods) < config.max_items:
            energy = self._morsel_energy()
            foods.append(self._morsel(world, len(foods) + 1, energy))
            covered += energy
        logger.info(
            "food.seeded count=%s total_energy=%.1f target=%.1f",
            len(foods),
            total_energy(foods),
            config.initial_total_energy,
        )
        return foods

    def top_up(
        self,
        foods: List[Food],
        world: IWorld,
        tick: int,
        abundance: float = 1.0,
    ) -> List[Food]:
        config = self._config
        if config.top_up_interval_ticks <= 0:
            return []
        if tick % config.top_up_interval_ticks != 0:
            return []
        deficit = config.target_total_energy * abundance - total_energy(foods)
        if deficit <= 0.0:
            return []

        spawned: List[Food] = []
        next_id = max([food.id for food in foods] + [0]) + 1
        while deficit > 0.0 and len(foods) + len(spawned) < config.max_items:
            energy = min(self._morsel_energy(), deficit)
            spawned.append(self._morsel(world, next_id, energy))
            next_id += 1
            deficit -= energy
        if spawned:
            logger.info(
                "food.topped_up count=%s energy=%.1f tick=%s abundance=%.2f",
                len(spawned),
                total_energy(spawned),
                tick,
                abundance,
            )
        return spawned
