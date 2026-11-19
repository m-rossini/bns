"""Interface for the food strategy.

Food is the renewable energy source: the strategy owns its full lifecycle —
seeding an initial amount, topping it back up toward a seasonal target, and
spoiling morsels over time. Placement and amounts are strategy-owned; the
container owns the food list and the lifecycle calls these hooks.
"""

from abc import ABC, abstractmethod
from typing import List

from sim.domain.food import Food
from sim.interfaces.world import IWorld


class IFoodStrategy(ABC):
    """Owns the full food lifecycle: seed, regrow and spoil."""

    @abstractmethod
    def initial_food(self, world: IWorld) -> List[Food]:
        """Morsels summing to the configured initial total energy."""

    @abstractmethod
    def top_up(
        self,
        foods: List[Food],
        world: IWorld,
        tick: int,
        abundance: float = 1.0,
        population_scale: float = 1.0,
    ) -> List[Food]:
        """This tick's regrowth from the resource-gradient field.

        Called every tick: new morsels spawn wherever the field is rich
        while the level sits below ``target × abundance × population_scale ×
        target_fraction``, wobbled per tick by ``±target_jitter`` so the level
        breathes instead of parking on a flat line. Returns an empty list when
        nothing is due (level at target, item cap reached, or no rich free
        spot found). ``abundance`` scales the effective target (seasonal
        growth); ``population_scale`` shrinks it with a shrinking population
        (per-capita food stays roughly flat); ``target_fraction`` steers the
        level toward a share of the target (default half).
        """

    @abstractmethod
    def decay(self, foods: List[Food]) -> int:
        """Spoil morsels for one tick, in place.

        Each morsel loses ``spoilage_per_tick`` energy (floored at zero).
        Returns the number of morsels fully depleted by this tick; the
        lifecycle removes those afterwards. A zero rate leaves food
        untouched.
        """

    @abstractmethod
    def get_state(self) -> dict:
        """Snapshot the evolving strategy state (rng + id counter)."""

    @abstractmethod
    def set_state(self, state: dict) -> None:
        """Restore evolving strategy state from a snapshot."""
