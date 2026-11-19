"""Random food spawn strategy: random morsel energies, strategy-placed start.

Morsel energies are drawn uniformly from ``[min_morsel_energy,
max_morsel_energy]``. The initial seeding asks the configured food placement
strategy (``FoodPlacementConfig``) for the whole morsel set, so the starting
distribution follows the selected strategy and is collision-free against the
world border, barriers and other morsels. Later regrowth is decided every
tick: up to ``tick_candidates`` spots are sampled and a morsel spawns
wherever the resource-gradient field is rich (noise >= threshold) while the
world is below ``target_total_energy × abundance × population_scale ×
target_fraction`` (season × living share × configured share, default half),
capped by ``max_items``.
The richness field is stable per placement seed (fixed phases, no rng draw
per evaluation), so rich patches persist instead of flickering. Snapshots
store the food list plus the strategy's rng/id state, so a resumed run keeps
its exact morsels and replays deterministically.
"""

import math
import random
from typing import List, Optional

from sim.config import FoodConfig
from sim.domain.food import Food, total_energy
from sim.domain.placement_utils import is_valid_bean_position
from sim.implementations.placement import build_placement_strategy
from sim.interfaces.food import IFoodStrategy
from sim.interfaces.placement import IPlacementStrategy
from sim.interfaces.world import IWorld
from sim.observability import get_logger

logger = get_logger("food.random")


class RandomFoodSpawnStrategy(IFoodStrategy):
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
        # Fixed phases for the richness field, derived from the placement
        # seed: rich patches stay put instead of flickering between ticks.
        phase_rng = random.Random(config.placement.seed)
        self._phase_x = phase_rng.uniform(0.0, 2.0 * math.pi)
        self._phase_y = phase_rng.uniform(0.0, 2.0 * math.pi)
        #: Next morsel id. Monotonic within a run so regrowth after a full
        #: wipe never reuses an id observed earlier in the same run.
        self._next_id = 1

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

    def get_state(self) -> dict:
        """Snapshot the evolving strategy state (rng + id counter)."""
        return {"rng_state": self._rng.getstate(), "next_id": self._next_id}

    def set_state(self, state: dict) -> None:
        """Restore evolving strategy state from a snapshot."""
        self._rng.setstate(state["rng_state"])
        self._next_id = int(state["next_id"])

    def _richness(self, x: float, y: float, freq: float) -> float:
        """Stable richness field in [0, 1] at a world position.

        Same sin/cos shape as the resource-gradient placement noise, but with
        fixed phases and no rng draw, so a spot's richness is identical on
        every tick and rich patches persist.
        """
        v = math.sin(x * freq + self._phase_x) * math.cos(
            y * freq + self._phase_y
        )
        return (v + 1.0) / 2.0

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
        foods = self._spawn(energies, positions, self._next_id)
        self._next_id += len(foods)
        logger.info(
            "food.seeded count=%s total_energy=%.1f target=%.1f",
            len(foods),
            total_energy(foods),
            config.initial_total_energy,
        )
        return foods

    def decay(self, foods: List[Food]) -> int:
        """Spoil morsels for one tick, in place; count the fully depleted."""
        rate = self._config.spoilage_per_tick
        if rate <= 0.0:
            return 0
        depleted = 0
        for food in foods:
            if food.energy <= 0.0:
                continue
            food.energy = max(0.0, food.energy - rate)
            if food.energy <= 0.0:
                depleted += 1
        return depleted

    def top_up(
        self,
        foods: List[Food],
        world: IWorld,
        tick: int,
        abundance: float = 1.0,
        population_scale: float = 1.0,
    ) -> List[Food]:
        """Decide this tick's regrowth from the resource-gradient field.

        Called every tick: up to ``tick_candidates`` spots are sampled and a
        morsel spawns wherever the field is rich (noise >= threshold) while
        the world is below ``target_total_energy × abundance ×
        population_scale × target_fraction``, wobbled per tick by
        ``±target_jitter`` so the level breathes instead of parking on a flat
        line. Capped by ``max_items``. Returns an empty list when the level is
        already at (or above) target. ``tick`` only labels the log line.
        """
        config = self._config
        jitter = 1.0
        if config.target_jitter > 0.0:
            jitter += self._rng.uniform(-config.target_jitter, config.target_jitter)
        target = (
            config.target_total_energy
            * abundance
            * population_scale
            * config.target_fraction
            * max(0.0, jitter)
        )
        covered = total_energy(foods)
        if covered >= target:
            return []
        if len(foods) >= config.max_items:
            return []

        grad = config.placement.resource_gradient
        freq = max(1e-6, grad.noise_frequency)
        threshold = max(0.0, min(1.0, grad.threshold))
        margin = self._margin(world)

        spawned: List[Food] = []
        candidates = list(foods)
        attempts = 0
        max_attempts = config.tick_candidates * 25
        while (
            len(spawned) < config.tick_candidates
            and attempts < max_attempts
            and covered < target
            and len(foods) + len(spawned) < config.max_items
        ):
            attempts += 1
            x = self._rng.uniform(0.0, world.width)
            y = self._rng.uniform(0.0, world.height)
            if (x < margin or x > world.width - margin
                    or y < margin or y > world.height - margin):
                continue
            if self._richness(x, y, freq) < threshold:
                continue
            if not is_valid_bean_position(
                x, y, config.food_radius, world, candidates
            ):
                continue
            remaining = target - covered
            if remaining <= 0.0:
                break
            energy = min(self._morsel_energy(), remaining)
            if energy <= 0.0:
                continue
            spawned.append(self._morsel(self._next_id, energy, (x, y)))
            self._next_id += 1
            candidates.append((x, y))
            covered += energy
        if spawned:
            logger.debug(
                "food.topped_up count=%s energy=%.1f tick=%s abundance=%.2f",
                len(spawned),
                total_energy(spawned),
                tick,
                abundance,
            )
        return spawned
