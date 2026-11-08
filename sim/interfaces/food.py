"""Interface for food spawn strategies.

Food is the renewable energy source: strategies seed an initial amount and
top it up towards a target total. Placement and amounts are strategy-owned;
the container owns the food list and the lifecycle calls these hooks.
"""

from abc import ABC, abstractmethod
from typing import List

from sim.domain.food import Food
from sim.interfaces.world import IWorld


class IFoodSpawnStrategy(ABC):
    """Seed and replenish food morsels."""

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
    ) -> List[Food]:
        """New morsels covering the deficit to ``target × abundance``.

        Returns an empty list on ticks where no top-up is due. ``abundance``
        scales the effective target (seasonal growth); ``1.0`` is neutral.
        """
