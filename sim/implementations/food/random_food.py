"""Random food spawn strategy: random morsel energies, strategy-placed start.

Morsel energies are drawn uniformly from ``[min_morsel_energy,
max_morsel_energy]``. The initial seeding asks the configured food placement
strategy (``FoodPlacementConfig``) for the whole morsel set, so the starting
distribution follows the selected strategy and is collision-free against the
world border, barriers and other morsels. Later top-ups use uniform random
positions validated against the same constraints, because incremental
top-ups cannot reuse a one-shot blue-noise layout without over-spacing the
new morsels. The initial seeding sums to ``initial_total_energy``; top-ups
cover the deficit to ``target_total_energy × abundance`` on
``top_up_interval_ticks`` boundaries, capped by ``max_items``. Snapshots store
the food list, so a resumed run keeps its exact morsels; ids restart from the
current maximum, so top-ups after a restore never collide.
"""

import random
from typing import List, Optional

from sim.config import FoodConfig
from sim.domain.food import Food, total_energy
from sim.domain.placement_utils import is_valid_bean_position
from sim.implementations.placement import build_placement_strategy
from sim.interfaces.food import IFoodSpawnStrategy
from sim.interfaces.placement import IPlacementStrategy
from sim.interfaces.world import IWorld
from sim.observability import get_logger

logger = get_logger("food.random")


class RandomFoodSpawnStrategy(IFoodSpawnStrategy):
    def __init__(
        self,
        config: FoodConfig,
        placement_strategy: Optional[IPlacementStrategy] = None,
    ):
        self._config = config
        self._rng = random.Random(config.seed)
        self._placement = placement_strategy or build_placement_strategy(
            config.placement
        )

    # ------------------------------------------------------------------
    # Placement
    # ------------------------------------------------------------------
    def _margin(self, world: IWorld) -> float:
        """Border margin in world units (``margin_cells``, capped to a quarter)."""
        config = self._config
        return min(
            config.margin_cells * world.cell_size,
            min(world.width, world.height) / 4.0,
        )

    def _placement_radius(self, world: IWorld) -> float:
        """Radius handed to the placement strategy.

        At least the morsel diameter (so two morsels can never overlap),
        enlarged by the border margin so the strategy also keeps morsels away
        from the world edge.
        """
        return max(2.0 * self._config.food_radius, self._margin(world))

    def _strategy_positions(self, world: IWorld, count: int) -> List[tuple]:
        """Initial placement: ask the configured strategy for ``count`` spots."""
        if count <= 0:
            return []
        return self._placement.generate_positions(
            count,
            world.width,
            world.height,
            world,
            [],
            radius=self._placement_radius(world),
        )

    def _random_positions(
        self,
        world: IWorld,
        count: int,
        existing: List[Food],
    ) -> List[tuple]:
        """Top-up placement: uniform random, collision-free against ``existing``.

        Collisions use the morsel radius (so morsels stay one diameter apart),
        while the configured ``margin_cells`` keeps them away from the border.
        """
        if count <= 0:
            return []
        config = self._config
        margin = self._margin(world)
        candidates = list(existing)
        positions: List[tuple] = []
        attempts = 0
        max_attempts = count * 200
        while len(positions) < count and attempts < max_attempts:
            attempts += 1
            x = self._rng.uniform(0.0, world.width)
            y = self._rng.uniform(0.0, world.height)
            if (x < margin or x > world.width - margin
                    or y < margin or y > world.height - margin):
                continue
            if not is_valid_bean_position(
                x, y, config.food_radius, world, candidates
            ):
                continue
            positions.append((x, y))
            candidates.append((x, y))
        return positions

    def _morsel(self, food_id: int, energy: float, position: tuple) -> Food:
        x, y = position
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

    def _energies(self, target: float, existing_count: int) -> List[float]:
        """Draw morsel energies summing to ``target`` (within one morsel)."""
        config = self._config
        energies: List[float] = []
        covered = 0.0
        while covered < target and existing_count + len(energies) < config.max_items:
            energy = self._morsel_energy()
            energies.append(energy)
            covered += energy
        return energies

    def _spawn(
        self,
        energies: List[float],
        positions: List[tuple],
        first_id: int,
    ) -> List[Food]:
        """Build morsels from energies and positions, trimming any shortfall."""
        if len(positions) < len(energies):
            logger.warning(
                "food.placement_shortfall requested=%d produced=%d",
                len(energies),
                len(positions),
            )
            energies = energies[: len(positions)]
        return [
            self._morsel(first_id + offset, energy, position)
            for offset, (energy, position) in enumerate(zip(energies, positions))
        ]

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------
    def initial_food(self, world: IWorld) -> List[Food]:
        config = self._config
        energies = self._energies(config.initial_total_energy, 0)
        positions = self._strategy_positions(world, len(energies))
        foods = self._spawn(energies, positions, 1)
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

        energies = self._energies(deficit, len(foods))
        positions = self._random_positions(world, len(energies), foods)
        next_id = max([food.id for food in foods] + [0]) + 1
        spawned = self._spawn(energies, positions, next_id)
        if spawned:
            logger.info(
                "food.topped_up count=%s energy=%.1f tick=%s abundance=%.2f",
                len(spawned),
                total_energy(spawned),
                tick,
                abundance,
            )
        return spawned
